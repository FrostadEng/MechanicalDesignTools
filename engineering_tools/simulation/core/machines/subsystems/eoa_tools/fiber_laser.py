import json
from pathlib import Path
from typing import Optional
from .base import ManufacturingTool
from engineering_tools.mech_core.standards.units import ureg, Q_
from engineering_tools.mech_core.standards.materials.steel import StructuralMaterial, get_material
from engineering_tools.mech_core.analysis.manufacturing.thermal_removal import (
    calculate_melting_speed,
    calculate_pierce_time
)
from engineering_tools.mech_core.analysis.fluid_dynamics.gas_jets import (
    calculate_nozzle_exit_velocity,
    calculate_clearing_speed_limit,
    calculate_gas_density_at_nozzle
)


class FiberLaser(ManufacturingTool):
    def __init__(self, config_file: str = "ipg_yyl_4kw.json"):
        # 1. Load Config
        base_path = Path(__file__).parent / "configs"
        with open(base_path / config_file, 'r') as f:
            self.config = json.load(f)

        # 2. Extract Physical Properties for the Robot
        specs = self.config['specs']

        super().__init__(
            name=self.config['model'],
            mass_kg=self.config['mass_kg'],
            tcp_offset=specs['tcp_offset_mm']
        )

        # 3. Setup Process Physics - Thermal Parameters
        self.power = Q_(specs['power_kw'], ureg.kW)
        self.efficiency = specs['efficiency_optical']

        proc = self.config['process_defaults']
        self.kerf_width = Q_(proc['kerf_width_mm'], ureg.mm)
        self.surface_condition = "mill_scale"  # Default surface condition

        # 4. Setup Process Physics - Fluid Dynamics Parameters
        self.gas_pressure = Q_(proc['gas_pressure_bar'], ureg.bar)
        self.nozzle_diameter = Q_(proc['nozzle_diameter_mm'], ureg.mm)
        self.gas_gamma = proc.get('gas_gamma', 1.4)  # Default for air/N2/O2
        self.efficiency_factor = proc.get('efficiency_factor', 0.1)

    def calculate_cutting_speed(self, material: StructuralMaterial, thickness_mm: float) -> float:
        """
        Calculate cutting speed using composite constraint model.

        Implements the composite constraint: cutting speed is limited by
        the MINIMUM of thermal (melting) and fluid dynamics (clearing) constraints.

        Args:
            material: StructuralMaterial with thermal properties
            thickness_mm: Material thickness in millimeters

        Returns:
            Cutting speed in mm/s (the slower of thermal or fluid limit)
        """
        # Convert thickness to quantity
        thickness = Q_(thickness_mm, ureg.mm)

        # Get surface absorption (laser-specific)
        absorptivity = 1.0
        try:
            surface = material.get_surface(self.surface_condition)
            absorptivity = surface.absorptivity_1um
        except (ValueError, KeyError):
            pass  # Use default absorptivity = 1.0

        # CONSTRAINT 1: Thermal Limit (material melting rate)
        v_thermal = calculate_melting_speed(
            material=material,
            thickness=thickness,
            tool_power=self.power,
            kerf_width=self.kerf_width,
            efficiency=self.efficiency,
            absorptivity=absorptivity
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

    def process_feature(self, env, robot, feature, beam):
        # 1. Mount Tool
        robot.mount_tool(self)

        # 2. GET PHYSICS FROM THE BEAM OBJECT
        # No more guessing "A36" or "10mm"
        material = beam.material
        thickness_mm = beam.get_thickness_at_feature(feature)

        # 3. Calculate Speed using composite constraint model
        speed_mm_s = self.calculate_cutting_speed(material, thickness_mm)

        # Log the decision
        # "Cutting 12.5mm Flange at 35mm/s"
        with robot.logger.log_event("Calc", "Physics", f"Thk:{thickness_mm:.1f}mm -> Spd:{speed_mm_s:.1f}mm/s"):
            pass

        # 4. Execute Motion (Continuous Path)
        # Laser assumes "Fly Cut" logic (no IHS dwell) unless specified

        # Move Rapid to Start
        # Note: We manually apply TCP offset here or let Robot handle it.
        # For this logic, we assume robot.move_rapid handles the TCP transform internally
        # (or we pass the raw coord and robot applies tool.tcp)
        yield from robot.move_rapid(feature.x_pos, feature.y_pos, 50.0) # Hover

        # Move to cut height
        yield from robot.move_linear(feature.x_pos, feature.y_pos, 0.0, speed_mm_s=200.0)

        # Cut
        with robot.logger.log_event("Cut", self.name, feature.feature_type):
             yield from robot.move_path(distance_mm=feature.path_length, speed_mm_s=speed_mm_s)

        # Retract
        yield from robot.move_rapid(feature.x_pos, feature.y_pos, 50.0)