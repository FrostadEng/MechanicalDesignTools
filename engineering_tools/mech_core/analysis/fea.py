"""
mech_core/analysis/fea.py
Frame analysis wrapper for PyNiteFEA integration with AISC library.
"""
from Pynite import FEModel3D
import matplotlib.pyplot as plt
import numpy as np
from ..units import ureg, Q_
from ..components.aisc_members import SectionProperties
from ..standards.materials import StructuralMaterial


class FrameAnalysis:
    """
    Wrapper for PyNiteFEA that integrates with mech_core AISC components.

    Handles mapping between AISC section properties and PyNite's FEA model,
    including correct axis transformations (Ix -> Iz for PyNite).

    Example:
        >>> from mech_core.units import ureg
        >>> from mech_core.components.aisc_members import get_section
        >>> from mech_core.standards.materials import get_material
        >>> from mech_core.analysis.fea import FrameAnalysis
        >>>
        >>> # Setup
        >>> frame = FrameAnalysis()
        >>> section = get_section("W12X26")
        >>> steel = get_material("ASTM A36")
        >>>
        >>> # Build model
        >>> frame.add_node("N1", 0, 0, 0)
        >>> frame.add_node("N2", 0, 0, 6)
        >>> frame.add_beam("B1", "N1", "N2", section, steel)
        >>>
        >>> # Apply loads and boundary conditions
        >>> frame.add_node_load("N2", Fx=10*ureg.kN)
        >>> frame.add_support("N1", "fixed")
        >>>
        >>> # Solve
        >>> frame.solve()
        >>>
        >>> # Get results
        >>> forces = frame.get_beam_forces("B1")
        >>> frame.generate_diagrams("B1", "beam_diagrams.png")
    """

    def __init__(self):
        """Initialize PyNite FEA model"""
        self.model = FEModel3D()
        self._material_counter = 0
        self._section_counter = 0
        self._material_map = {}  # Track material names
        self._section_map = {}   # Track section names

    def add_node(self, name: str, x: float, y: float, z: float):
        """
        Add a node to the model.

        Args:
            name: Node identifier (e.g., "N1")
            x, y, z: Coordinates in meters (float or Pint quantity)
        """
        # Convert Pint quantities to float if needed
        if hasattr(x, 'magnitude'):
            x = x.to(ureg.meter).magnitude
        if hasattr(y, 'magnitude'):
            y = y.to(ureg.meter).magnitude
        if hasattr(z, 'magnitude'):
            z = z.to(ureg.meter).magnitude

        self.model.add_node(name, x, y, z)

    def add_beam(
        self,
        name: str,
        start_node: str,
        end_node: str,
        section: SectionProperties,
        material: StructuralMaterial,
        rotation: float = 0.0
    ):
        """
        Add a beam member with AISC section properties.

        Critical: Maps AISC coordinate system to PyNite:
        - AISC Ix (strong axis) -> PyNite Iz
        - AISC Iy (weak axis) -> PyNite Iy
        - AISC J (torsion) -> PyNite J

        Args:
            name: Member identifier (e.g., "B1")
            start_node: Starting node name
            end_node: Ending node name
            section: SectionProperties from AISC database
            material: StructuralMaterial (steel grade)
            rotation: Member rotation angle in degrees (default 0)
        """
        # Register material if not already added
        mat_name = self._get_or_add_material(material)

        # Register section with correct axis mapping
        sec_name = self._get_or_add_section(section)

        # Add member to model
        self.model.add_member(
            name=name,
            i_node=start_node,
            j_node=end_node,
            material_name=mat_name,
            section_name=sec_name,
            rotation=rotation
        )

    def _get_or_add_material(self, material: StructuralMaterial) -> str:
        """Register material with PyNite if not already added"""
        # Use material name as key
        if material.name in self._material_map:
            return self._material_map[material.name]

        # Create unique material name
        mat_name = f"MAT_{self._material_counter}"
        self._material_counter += 1

        # Convert material properties to base units (Pa, kg/m^3)
        E = material.elastic_modulus.to(ureg.pascal).magnitude
        G = E / (2 * (1 + 0.3))  # Assume Poisson's ratio = 0.3 for steel
        nu = 0.3
        rho = material.density.to(ureg.kg / ureg.meter**3).magnitude

        # Add to PyNite
        self.model.add_material(mat_name, E, G, nu, rho)

        # Track mapping
        self._material_map[material.name] = mat_name
        return mat_name

    def _get_or_add_section(self, section: SectionProperties) -> str:
        """
        Register section with PyNite if not already added.

        CRITICAL AXIS MAPPING:
        PyNite uses a different coordinate convention than AISC:
        - PyNite Iy = AISC Iy (weak axis - same)
        - PyNite Iz = AISC Ix (strong axis - SWAPPED!)
        - PyNite J = AISC J (torsion - same)
        """
        # Use section name as key
        if section.name in self._section_map:
            return self._section_map[section.name]

        # Create unique section name
        sec_name = f"SEC_{self._section_counter}"
        self._section_counter += 1

        # Convert section properties to base units (m^2, m^4)
        A = section.A.to(ureg.meter**2).magnitude

        # CRITICAL: Axis swap for PyNite convention
        Iz = section.Ix.to(ureg.meter**4).magnitude  # Strong axis -> Iz in PyNite
        Iy = section.Iy.to(ureg.meter**4).magnitude  # Weak axis -> Iy in PyNite
        J = section.J.to(ureg.meter**4).magnitude    # Torsion constant

        # Add to PyNite
        self.model.add_section(sec_name, A, Iz, Iy, J)

        # Track mapping
        self._section_map[section.name] = sec_name
        return sec_name

    def add_support(self, node_name: str, support_type: str = "fixed"):
        """
        Add support/boundary condition to a node.

        Args:
            node_name: Node identifier
            support_type: "fixed", "pinned", or "roller"
        """
        if support_type == "fixed":
            self.model.def_support(node_name, True, True, True, True, True, True)
        elif support_type == "pinned":
            self.model.def_support(node_name, True, True, True, False, False, False)
        elif support_type == "roller":
            self.model.def_support(node_name, True, True, False, False, False, False)
        else:
            raise ValueError(f"Unknown support type: {support_type}. Use 'fixed', 'pinned', or 'roller'")

    def add_node_load(
        self,
        node_name: str,
        Fx: Q_ = None,
        Fy: Q_ = None,
        Fz: Q_ = None,
        Mx: Q_ = None,
        My: Q_ = None,
        Mz: Q_ = None,
        case: str = "Case 1"
    ):
        """
        Add concentrated load to a node.

        Args:
            node_name: Node identifier
            Fx, Fy, Fz: Forces in X, Y, Z directions (Pint quantities)
            Mx, My, Mz: Moments about X, Y, Z axes (Pint quantities)
            case: Load case name
        """
        # Convert to base units (N, N*m)
        fx = Fx.to(ureg.newton).magnitude if Fx is not None else 0
        fy = Fy.to(ureg.newton).magnitude if Fy is not None else 0
        fz = Fz.to(ureg.newton).magnitude if Fz is not None else 0
        mx = Mx.to(ureg.newton * ureg.meter).magnitude if Mx is not None else 0
        my = My.to(ureg.newton * ureg.meter).magnitude if My is not None else 0
        mz = Mz.to(ureg.newton * ureg.meter).magnitude if Mz is not None else 0

        self.model.add_node_load(node_name, 'FX', fx, case)
        self.model.add_node_load(node_name, 'FY', fy, case)
        self.model.add_node_load(node_name, 'FZ', fz, case)
        self.model.add_node_load(node_name, 'MX', mx, case)
        self.model.add_node_load(node_name, 'MY', my, case)
        self.model.add_node_load(node_name, 'MZ', mz, case)

    def add_member_dist_load(
        self,
        member_name: str,
        direction: str,
        w1: Q_,
        w2: Q_,
        x1: Q_ = None,
        x2: Q_ = None,
        case: str = "Case 1"
    ):
        """
        Add distributed load to a member.

        Args:
            member_name: Member identifier
            direction: "Fx", "Fy", "Fz" (force direction)
            w1: Load intensity at start (force/length)
            w2: Load intensity at end (force/length)
            x1: Start position (default: 0)
            x2: End position (default: member length)
            case: Load case name
        """
        # Convert to base units (N/m)
        w1_val = w1.to(ureg.newton / ureg.meter).magnitude
        w2_val = w2.to(ureg.newton / ureg.meter).magnitude
        x1_val = x1.to(ureg.meter).magnitude if x1 is not None else 0
        x2_val = x2.to(ureg.meter).magnitude if x2 is not None else None

        self.model.add_member_dist_load(
            member_name, direction, w1_val, w2_val, x1_val, x2_val, case
        )

    def solve(self, check_statics: bool = False):
        """
        Solve the FEA model.

        Args:
            check_statics: Perform static equilibrium check (default False)
        """
        self.model.analyze(check_statics=check_statics)

    def get_beam_forces(self, member_name: str) -> dict:
        """
        Get maximum shear and moment forces for a beam.

        Args:
            member_name: Member identifier

        Returns:
            Dictionary with:
                - max_shear_y: Maximum shear in Y direction (kN)
                - max_shear_z: Maximum shear in Z direction (kN)
                - max_moment_y: Maximum moment about Y axis (kN*m)
                - max_moment_z: Maximum moment about Z axis (kN*m)  [Strong axis!]
                - min_shear_y, min_shear_z: Minimum values
                - min_moment_y, min_moment_z: Minimum values
        """
        member = self.model.members[member_name]

        # Sample member along its length
        n_points = 50
        L = member.L()
        positions = np.linspace(0, L, n_points)

        # Collect forces at each position
        shear_y = []
        shear_z = []
        moment_y = []
        moment_z = []

        for x in positions:
            shear_y.append(member.shear('Fy', x))
            shear_z.append(member.shear('Fz', x))
            moment_y.append(member.moment('My', x))
            moment_z.append(member.moment('Mz', x))  # Strong axis moment!

        return {
            'max_shear_y': max(shear_y) / 1000 * ureg.kN,  # Convert N -> kN
            'min_shear_y': min(shear_y) / 1000 * ureg.kN,
            'max_shear_z': max(shear_z) / 1000 * ureg.kN,
            'min_shear_z': min(shear_z) / 1000 * ureg.kN,
            'max_moment_y': max(moment_y) / 1000 * ureg.kN * ureg.meter,  # Convert N*m -> kN*m
            'min_moment_y': min(moment_y) / 1000 * ureg.kN * ureg.meter,
            'max_moment_z': max(moment_z) / 1000 * ureg.kN * ureg.meter,  # STRONG AXIS
            'min_moment_z': min(moment_z) / 1000 * ureg.kN * ureg.meter,
        }

    def generate_diagrams(
        self,
        member_name: str,
        output_path: str,
        direction: str = "strong_axis"
    ):
        """
        Generate shear and moment diagrams for a beam member.

        Args:
            member_name: Member identifier
            output_path: Path to save diagram (e.g., "beam_diagrams.png")
            direction: "strong_axis" (Mz) or "weak_axis" (My)
        """
        member = self.model.members[member_name]

        # Sample along member length
        n_points = 100
        L = member.L()
        positions = np.linspace(0, L, n_points)

        # Collect forces
        if direction == "strong_axis":
            # Strong axis bending (Mz) and associated shear (Fy)
            shear = [member.shear('Fy', x) / 1000 for x in positions]  # kN
            moment = [member.moment('Mz', x) / 1000 for x in positions]  # kN*m
            title_suffix = "(Strong Axis - Mz)"
        else:
            # Weak axis bending (My) and associated shear (Fz)
            shear = [member.shear('Fz', x) / 1000 for x in positions]  # kN
            moment = [member.moment('My', x) / 1000 for x in positions]  # kN*m
            title_suffix = "(Weak Axis - My)"

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Shear diagram
        ax1.plot(positions, shear, 'b-', linewidth=2)
        ax1.fill_between(positions, shear, alpha=0.3)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel('Shear (kN)', fontsize=12)
        ax1.set_title(f'Shear Force Diagram {title_suffix}', fontsize=14, fontweight='bold')
        ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        # Moment diagram
        ax2.plot(positions, moment, 'r-', linewidth=2)
        ax2.fill_between(positions, moment, alpha=0.3, color='red')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlabel('Position along member (m)', fontsize=12)
        ax2.set_ylabel('Moment (kN*m)', fontsize=12)
        ax2.set_title(f'Bending Moment Diagram {title_suffix}', fontsize=14, fontweight='bold')
        ax2.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        # Add max/min annotations
        max_shear_idx = np.argmax(np.abs(shear))
        max_moment_idx = np.argmax(np.abs(moment))

        ax1.annotate(
            f'Max: {shear[max_shear_idx]:.2f} kN',
            xy=(positions[max_shear_idx], shear[max_shear_idx]),
            xytext=(10, 10), textcoords='offset points',
            bbox=dict(boxstyle='round', fc='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )

        ax2.annotate(
            f'Max: {moment[max_moment_idx]:.2f} kN*m',
            xy=(positions[max_moment_idx], moment[max_moment_idx]),
            xytext=(10, 10), textcoords='offset points',
            bbox=dict(boxstyle='round', fc='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Diagrams saved to: {output_path}")
