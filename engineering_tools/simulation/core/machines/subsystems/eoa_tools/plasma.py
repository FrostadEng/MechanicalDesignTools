import json
import math
from pathlib import Path
from .base import ManufacturingTool
from engineering_tools.mech_core.standards.materials.steel import StructuralMaterial, get_material
from engineering_tools.mech_core.standards.units import ureg, Q_
from engineering_tools.mech_core.analysis.manufacturing.thermal_removal import calculate_melting_speed
from engineering_tools.mech_core.analysis.fluid_dynamics.gas_jets import (
    calculate_nozzle_exit_velocity,
    calculate_clearing_speed_limit,
    calculate_gas_density_at_nozzle
)

class PlasmaTorch(ManufacturingTool):
    def __init__(self, config_file: str = "hypertherm_xpr300.json"):
        # 1. Load Config
        base_path = Path(__file__).parent / "configs"
        with open(base_path / config_file, 'r') as f:
            self.config = json.load(f)

        specs = self.config['specs']
        proc = self.config['process_defaults']

        super().__init__(
            name=self.config['model'],
            mass_kg=self.config['mass_kg'],
            tcp_offset=specs['tcp_offset_mm']
        )
        
        # Thermal parameters
        self.power = Q_(specs['power_kw'], ureg.kW)
        self.efficiency = specs['efficiency_thermal']
        self.kerf_width = Q_(proc['kerf_width_mm'], ureg.mm)

        # Timings
        self.pierce_delay_sec = proc['pierce_delay_sec']
        self.ihs_time_sec = proc['ihs_time_sec']
        self.retract_dist_mm = proc['retract_dist_mm']

        # Fluid dynamics parameters
        self.gas_pressure = Q_(proc['gas_pressure_bar'], ureg.bar)
        self.nozzle_diameter = Q_(proc['nozzle_diameter_mm'], ureg.mm)
        self.gas_gamma = proc.get('gas_gamma', 1.4)  # Default for air/N2/O2
        self.efficiency_factor = proc.get('efficiency_factor', 0.1)

    def calculate_cut_speed(self, material: StructuralMaterial, thickness_mm: float) -> float:
        """
        Calculate cutting speed using composite constraint model.

        Implements the composite constraint: cutting speed is limited by
        the MINIMUM of thermal (melting) and fluid dynamics (clearing) constraints.

        Note: Plasma torches don't use surface absorptivity (set to 1.0),
        as the plasma arc interacts differently than laser light.

        Args:
            material: StructuralMaterial with thermal properties
            thickness_mm: Material thickness in millimeters

        Returns:
            Cutting speed in mm/s (the slower of thermal or fluid limit)
        """
        # Convert thickness to quantity
        thickness = Q_(thickness_mm, ureg.mm)

        # CONSTRAINT 1: Thermal Limit (material melting rate)
        # Plasma doesn't use surface absorptivity - set to 1.0
        v_thermal = calculate_melting_speed(
            material=material,
            thickness=thickness,
            tool_power=self.power,
            kerf_width=self.kerf_width,
            efficiency=self.efficiency,
            absorptivity=1.0  # Plasma arc interaction, not surface-dependent
        )

        # CONSTRAINT 2: Fluid Dynamics Limit (molten material clearing rate)
        v_gas = calculate_nozzle_exit_velocity(
            pressure_inlet=self.gas_pressure,
            pressure_ambient=Q_(1.0, ureg.bar),  # Atmospheric pressure
            temperature_inlet=Q_(300, ureg.K),   # Room temperature assumption
            gas_gamma=self.gas_gamma
        )

        gas_density = calculate_gas_density_at_nozzle(
            pressure=self.gas_pressure,
            temperature=Q_(300, ureg.K),
            gas_mw=28.97  # Air molecular weight
        )

        v_clearing = calculate_clearing_speed_limit(
            nozzle_velocity=v_gas,
            nozzle_diameter=self.nozzle_diameter,
            kerf_width=self.kerf_width,
            material_density=material.density,
            gas_density=gas_density,
            efficiency_factor=self.efficiency_factor
        )

        # COMPOSITE CONSTRAINT: Worst case wins (minimum speed)
        v_constrained = min(v_thermal, v_clearing)

        # Convert back to mm/s float for simulation compatibility
        return v_constrained.to(ureg.mm / ureg.second).magnitude

    def process_feature(self, env, robot, feature):
        # 1. Mount Tool (Updates Robot Dynamics - Heavy!)
        robot.mount_tool(self)
        
        # 2. Physics Speed
        mat = get_material("ASTM A36")
        speed_mm_s = self.calculate_cut_speed(mat, thickness_mm=10.0)
        
        # 3. Execute Sequence
        # Move Rapid (Slowed by heavy tool)
        yield from robot.move_rapid(feature.x_pos, feature.y_pos, self.retract_dist_mm)
        
        # IHS Sequence
        with robot.logger.log_event("IHS", self.name):
            yield from robot.move_linear(feature.x_pos, feature.y_pos, 0.0, speed_mm_s=50.0)
            yield env.timeout(self.ihs_time_sec)
        
        # Pierce
        with robot.logger.log_event("Pierce", self.name):
            yield env.timeout(self.pierce_delay_sec)
        
        # Cut
        cut_len = feature.path_length if feature.path_length > 0 else (math.pi * feature.diameter)
        with robot.logger.log_event("Cut", self.name, feature.feature_type):
            yield from robot.move_path(distance_mm=cut_len, speed_mm_s=speed_mm_s)
            
        # Retract
        yield from robot.move_rapid(feature.x_pos, feature.y_pos, self.retract_dist_mm)