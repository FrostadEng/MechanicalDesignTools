"""
Fin Plate Shear Connection Component

A "dumb" component that holds geometry and delegates validation to code layers.
Calculates geometric properties (Net Area, etc.) before calling code validators.
"""
from mech_core.components.members.aisc import SectionProperties
from mech_core.standards.materials import StructuralMaterial
from mech_core.codes.structural.csa_s16 import connections as csa_conn
from mech_core.standards.units import ureg, Q_


class FinPlateConnection:
    """
    Fin plate shear connection component.
    """

    def __init__(
        self,
        beam: SectionProperties,
        column: SectionProperties,
        plate_thickness: Q_,
        plate_depth: Q_,
        plate_material: StructuralMaterial, # ADDED: Need this for Fu/Fy
        beam_material: StructuralMaterial,  # ADDED: Need this for Web checks
        bolt_pattern: dict,  # e.g., {'rows': 3, 'spacing': 75*ureg.mm, 'edge_v': 35*ureg.mm, 'edge_h': 35*ureg.mm}
        bolt_spec: dict      # e.g., {'diameter': 20*ureg.mm, 'grade': 'A325'}
    ):
        self.beam = beam
        self.column = column
        self.plate_thickness = plate_thickness
        self.plate_depth = plate_depth
        self.plate_material = plate_material
        self.beam_material = beam_material

        # Store the full dicts for later access
        self.bolt_pattern = bolt_pattern
        self.bolt_spec = bolt_spec

        # Defaults for pattern if not fully specified
        self.rows = bolt_pattern.get('rows', 3)
        self.spacing = bolt_pattern.get('spacing', 75 * ureg.mm)
        self.edge_v = bolt_pattern.get('edge_v', 35 * ureg.mm) # Vertical edge dist
        self.edge_h = bolt_pattern.get('edge_h', 35 * ureg.mm) # Horizontal edge dist

        self.db = bolt_spec.get('diameter', 19.05 * ureg.mm) # 3/4" default
        self.grade = bolt_spec.get('grade', "ASTM A325")

    def analyze(self, factored_shear: Q_, code: str = 'csa_s16') -> dict:
        """
        Validate connection against specified code for a given load.
        """
        if code == 'csa_s16':
            return self._analyze_csa_s16(factored_shear)
        else:
            raise NotImplementedError(f"Code {code} not yet supported")

    def _analyze_csa_s16(self, Vf: Q_) -> dict:
        """
        Internal CSA S16 check logic.
        """
        # 1. Setup
        # Assume 2 vertical columns of bolts standard for fin plates > 1 col
        # If rows=2, total=4 bolts.
        # Logic: If bolt_pattern has 'columns', use it. Else assume 1 column? 
        # Standard Fin plates usually 1 column unless wide. Let's assume 1 column for the MVP logic 
        # based on your previous 'rows' input, but let's be robust:
        n_cols = self.bolt_pattern.get('cols', 1)
        n_rows = self.bolt_pattern['rows']
        n_bolts = n_rows * n_cols
        
        d_b = self.bolt_spec['diameter']
        grade = self.bolt_spec['grade']
        
        # 2. RUN CHECKS (Delegate to Code Layer)
        results = {}
        
        # A. Bolt Shear
        results['bolt_shear'] = csa_conn.check_bolt_shear(
            n_bolts=n_bolts,
            bolt_diameter=d_b,
            bolt_grade=grade,
            factored_shear=Vf
        )
        
        # B. Bearing (Check both Plate and Beam Web)
        # We need end distance. Vertical edge distance usually governs bearing.
        e_dist = self.bolt_pattern.get('edge_v', 35*ureg.mm)
        
        # Check Plate Bearing
        res_bear_plate = csa_conn.check_bearing(
            bolt_diameter=d_b,
            plate_thickness=self.plate_thickness,
            end_distance=e_dist,
            material=self.plate_material,
            factored_force=Vf/n_bolts, # Per bolt
            member_name="Fin Plate"
        )

        # Check Beam Web Bearing
        res_bear_beam = csa_conn.check_bearing(
            bolt_diameter=d_b,
            plate_thickness=self.beam.tw,
            end_distance=e_dist, # Assume same edge dist for simplicity or calculate
            material=self.beam_material,
            factored_force=Vf/n_bolts,
            member_name="Beam Web"
        )
        
        # Take worst case for reporting
        if res_bear_plate['utilization'] > res_bear_beam['utilization']:
            results['bearing'] = res_bear_plate
        else:
            results['bearing'] = res_bear_beam

        # C. Block Shear (Beam Web is usually critical)
        # Calculate Areas (Geometry logic stays in Component)
        # Vertical Line Length (Shear)
        s = self.bolt_pattern['spacing']
        L_gv = (n_rows - 1) * s + e_dist
        t_web = self.beam.tw
        
        # Gross Shear Area
        Agv = L_gv * t_web
        
        # Net Shear Area (minus holes)
        # Hole = d + 2mm
        h_dia = d_b + 2*ureg.mm
        Anv = (L_gv - (n_rows - 0.5) * h_dia) * t_web
        
        # Net Tension Area (Horizontal leg)
        # Edge horizontal
        e_h = self.bolt_pattern.get('edge_h', 35*ureg.mm)
        Ant = (e_h - 0.5 * h_dia) * t_web
        
        results['block_shear'] = csa_conn.check_block_shear(
            Agv=Agv,
            Anv=Anv,
            Ant=Ant,
            material=self.beam_material,
            factored_force=Vf, # Map 'Vf' to the generic 'factored_force'
            Ubs=1.0
        )

        # 3. AGGREGATE RESULTS
        # Combine traces for a "Master Trace" if needed
        traces = []
        traces.extend(results['bolt_shear']['calc_trace'])
        traces.extend(results['bearing']['calc_trace'])
        traces.extend(results['block_shear']['calc_trace'])
        
        # Determine Critical Mode
        modes = [
            (results['bolt_shear']['utilization'], "Bolt Shear"),
            (results['bearing']['utilization'], "Bearing"),
            (results['block_shear']['utilization'], "Block Shear")
        ]
        crit_util, crit_mode = max(modes)
        overall = "PASS" if crit_util <= 1.0 else "FAIL"

        return {
            'overall_status': overall,
            'critical_mode': f"{crit_mode} ({crit_util:.2f})",
            'calc_trace': traces,
            'load_case': {'Vf': Vf},
            # EXPOSE SUB-RESULTS
            'bolt_shear': results['bolt_shear'],
            'bearing': results['bearing'],
            'block_shear': results['block_shear']
        }