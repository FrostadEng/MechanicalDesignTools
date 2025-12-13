import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
from mech_core.standards.materials import StructuralMaterial, ConcreteMaterial

class BasePlateDesign:
    """
    Design of Column Base Plates for Axial Compression.
    Follows principles of AISC Design Guide 1 / CSA S16.
    """
    def __init__(
        self, 
        column: SectionProperties, 
        load_Pu: Q_, 
        steel_grade: StructuralMaterial,
        concrete: ConcreteMaterial,
        plate_width_B: Q_ = None,  # Optional: If None, we calculate min
        plate_length_N: Q_ = None  # Optional: If None, we calculate min
    ):
        self.col = column
        self.Pu = load_Pu
        self.steel = steel_grade
        self.conc = concrete
        
        # Dimensions (B = perpendicular to web, N = parallel to web)
        # If not provided, we will start with geometry + 2 inches (50mm) padding
        padding = 50 * ureg.mm
        self.B = plate_width_B if plate_width_B else (self.col.bf + 2*padding)
        self.N = plate_length_N if plate_length_N else (self.col.d + 2*padding)
        
    def analyze(self):
        """
        Performs the check and returns a 'Step-by-Step' report dictionary.
        """
        report = {}
        report['header'] = f"Base Plate Analysis for {self.col.name}"
        
        # 1. GEOMETRY CHECK
        A1 = self.B * self.N
        report['step_1'] = {
            "desc": "Plate Geometry",
            "B": self.B,
            "N": self.N,
            "Area": A1.to(ureg.mm**2)
        }
        
        # 2. CONCRETE BEARING CHECK
        # CSA S16: Br = 0.85 * phi_c * fc * A1 (Assume no confinement A2/A1 for conservative calc)
        # phi_c = 0.65
        phi_c = self.conc.phi_c
        fc = self.conc.fc_prime
        
        # Stress on concrete (q)
        bearing_stress = self.Pu / A1
        bearing_capacity = 0.85 * phi_c * fc
        
        ratio_bearing = bearing_stress / bearing_capacity
        status_bearing = "PASS" if ratio_bearing <= 1.0 else "FAIL"
        
        report['step_2'] = {
            "desc": "Concrete Bearing Resistance (CSA S16)",
            "Load (Pu)": self.Pu.to(ureg.kN),
            "Bearing Stress (q)": bearing_stress.to(ureg.MPa),
            "Allowable Stress (0.85*phi*fc)": bearing_capacity.to(ureg.MPa),
            "Ratio": ratio_bearing.to("dimensionless").magnitude,
            "Status": status_bearing
        }
        
        # 3. PLATE BENDING (THICKNESS)
        # AISC Design Guide 1 / CSA Common Practice
        # We calculate the cantilever dimensions m and n
        
        # m (Cantilever in N direction, parallel to depth)
        # m = (N - 0.95*d) / 2
        m = (self.N - 0.95 * self.col.d) / 2
        
        # n (Cantilever in B direction, parallel to flange)
        # n = (B - 0.8*bf) / 2
        n = (self.B - 0.8 * self.col.bf) / 2
        
        # Governing cantilever dimension
        l_cant = max(m, n, 0 * ureg.mm) # Ensure non-negative
        
        # Required Thickness formula (based on Uniform Bearing assumption)
        # t_req = l * sqrt( (2 * Pu) / (0.9 * Fy * Area) )
        # Note: In CSA, phi_steel = 0.9
        phi_s = 0.9
        Fy = self.steel.yield_strength
        
        term_under_root = (2 * self.Pu) / (phi_s * Fy * A1)
        # Make sure term is dimensionless math or handled correctly
        # [Force] / [Stress * Area] -> [Force] / [Force] -> Dimensionless. Good.
        
        t_req = l_cant * np.sqrt(term_under_root.to("dimensionless").magnitude)

        # Get standard thickness from inventory
        from mech_core.standards.materials import stock

        if not stock.check_availability(self.steel.name, "plate"):
            print(f"[WARNING] {self.steel.name} not in plate database. Using calculated thickness.")
            t_standard = t_req
        else:
            t_standard = stock.get_plate_thickness(t_req, system="metric")

        report['step_3'] = {
            "desc": "Plate Thickness Calculation",
            "Cantilever m": m.to(ureg.mm),
            "Cantilever n": n.to(ureg.mm),
            "Critical Length (l)": l_cant.to(ureg.mm),
            "t_required": t_req.to(ureg.mm),
            "t_standard": t_standard.to(ureg.mm)
        }

        report['summary'] = {
            "Recommended Plate": f"{self.B:.0f~} x {self.N:.0f~}",
            "Min Thickness": f"{t_req:.2f~}",
            "Standard Thickness": f"{t_standard:.1f~}",
            "Global Status": "PASS" if status_bearing == "PASS" else "FAIL"
        }
        
        return report

    def generate_markdown(self):
        """Returns a string formatted as a mini-report"""
        res = self.analyze()
        lines = []
        lines.append(f"### {res['header']}") 
        lines.append(f"**Load:** {self.Pu.to(ureg.kN):.2f~} | **Col:** {self.col.name}")
        lines.append(f"**Mat:** {self.steel.name} | **Conc:** {self.conc.name}")
        
        # Loop through steps
        for key, step in res.items():
            if key.startswith("step"):
                lines.append(f"#### {step['desc']}") 
                for k, v in step.items():
                    if k != 'desc':
                        if hasattr(v, 'magnitude'):
                            # The :~ format specifier tells Pint to use short units (mm, kN)
                            lines.append(f"- **{k}:** {v:.3f~}") 
                        else:
                            lines.append(f"- **{k}:** {v}")
                lines.append("")
        
        summ = res['summary']
        lines.append("#### CONCLUSION")
        lines.append(f"> **Status:** {summ['Global Status']}")
        lines.append(f"> **Calculated Thickness:** {summ['Min Thickness']}")
        lines.append(f"> **Purchase Plate:** {summ['Recommended Plate']} x **{summ['Standard Thickness']}**")
        lines.append("---")
        
        return "\n".join(lines)