"""
Bolted Joint Analysis Module

Analysis of bolted connections including:
- Preload calculations
- Joint stiffness
- External load distribution
- Factor of safety against joint separation and bolt failure

Based on VDI 2230 and Shigley's Mechanical Engineering Design.
This is where the "scribbles logic" lives - the mathematical solvers.
"""

import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class BoltedJointGeometry:
    """
    Geometric parameters for a bolted joint.

    Attributes:
        bolt_diameter: Nominal bolt diameter in mm
        thread_pitch: Thread pitch in mm
        grip_length: Total grip length (clamped material thickness) in mm
        head_diameter: Bolt head or washer diameter in mm
        through_hole_diameter: Through hole diameter in clamped material in mm
        num_bolts: Number of bolts in the joint (default: 1)
    """
    bolt_diameter: float
    thread_pitch: float
    grip_length: float
    head_diameter: float
    through_hole_diameter: float
    num_bolts: int = 1


@dataclass
class BoltedJointMaterials:
    """
    Material properties for bolted joint.

    Attributes:
        bolt_modulus: Bolt elastic modulus in GPa
        member_modulus: Clamped member elastic modulus in GPa
        bolt_yield: Bolt yield strength in MPa
        friction_coefficient: Coefficient of friction (default: 0.15 for steel on steel)
    """
    bolt_modulus: float
    member_modulus: float
    bolt_yield: float
    friction_coefficient: float = 0.15


class BoltedJoint:
    """
    Represents a bolted joint for analysis.

    Combines geometry, materials, and loading to analyze joint performance.
    """

    def __init__(self, geometry: BoltedJointGeometry, materials: BoltedJointMaterials,
                 stress_area: float):
        """
        Initialize bolted joint analysis.

        Args:
            geometry: BoltedJointGeometry object
            materials: BoltedJointMaterials object
            stress_area: Thread stress area in mm^2 (from standards)
        """
        self.geom = geometry
        self.mat = materials
        self.stress_area = stress_area

        # Calculate stiffnesses
        self.k_bolt = self._calculate_bolt_stiffness()
        self.k_member = self._calculate_member_stiffness()

    def _calculate_bolt_stiffness(self) -> float:
        """
        Calculate bolt stiffness using simplified model.

        k_bolt = (A_s * E_bolt) / L_grip

        Returns:
            Bolt stiffness in N/mm
        """
        E = self.mat.bolt_modulus * 1000  # Convert GPa to MPa (N/mm^2)
        L = self.geom.grip_length

        k_bolt = (self.stress_area * E) / L

        return k_bolt

    def _calculate_member_stiffness(self) -> float:
        """
        Calculate member stiffness using frustum approximation.

        Based on VDI 2230 method using equivalent frustum area.

        Returns:
            Member stiffness in N/mm
        """
        E = self.mat.member_modulus * 1000  # Convert GPa to MPa

        # Frustum half-angle (typical value for through-hole joints)
        alpha = np.radians(30)  # 30 degrees

        d_h = self.geom.through_hole_diameter
        d_w = self.geom.head_diameter
        L = self.geom.grip_length

        # Calculate equivalent diameter at the end of frustum
        d_sub = min(d_h + L * np.tan(alpha), d_w + L * np.tan(alpha))

        # Simplified frustum stiffness formula
        # This is an approximation - full VDI 2230 is more complex
        A_sub = np.pi * (d_sub ** 2 - d_h ** 2) / 4

        if A_sub <= 0:
            # Fallback if geometry is problematic
            A_sub = np.pi * d_h ** 2 / 4

        k_member = (A_sub * E) / L

        return k_member

    def get_stiffness_ratio(self) -> float:
        """
        Calculate joint stiffness ratio.

        C = k_bolt / (k_bolt + k_member)

        This determines how external load is distributed between bolt and members.

        Returns:
            Stiffness ratio (0 to 1)
        """
        C = self.k_bolt / (self.k_bolt + self.k_member)
        return C

    def calculate_preload_from_torque(self, torque: float,
                                     k_factor: float = 0.2) -> float:
        """
        Calculate bolt preload from applied torque.

        T = k * d * F_preload

        Args:
            torque: Applied torque in Nm
            k_factor: Torque coefficient (default: 0.2 for dry steel)

        Returns:
            Bolt preload in N
        """
        d = self.geom.bolt_diameter / 1000  # Convert mm to meters

        F_preload = (torque / k_factor) / d

        return F_preload

    def analyze_external_load(self, preload: float, external_load: float
                             ) -> Dict[str, float]:
        """
        Analyze joint under external tensile load.

        Calculates bolt load, member load, and factors of safety.

        Args:
            preload: Initial bolt preload in N
            external_load: External tensile load on joint in N

        Returns:
            Dictionary containing:
                - bolt_load: Total load in bolt (N)
                - member_load: Remaining compression in members (N)
                - separation_safety: Factor of safety against joint separation
                - yield_safety: Factor of safety against bolt yield
                - load_factor: Fraction of external load carried by bolt
        """
        C = self.get_stiffness_ratio()

        # Load distribution (per bolt if multiple)
        P_ext_per_bolt = external_load / self.geom.num_bolts

        # Load carried by bolt
        delta_F_bolt = C * P_ext_per_bolt

        # Total bolt load
        F_bolt_total = preload + delta_F_bolt

        # Remaining compression in members
        F_member = preload - (1 - C) * P_ext_per_bolt

        # Bolt stress
        sigma_bolt = F_bolt_total / self.stress_area

        # Factor of safety against joint separation
        if P_ext_per_bolt > 0:
            FS_separation = preload / ((1 - C) * P_ext_per_bolt)
        else:
            FS_separation = float('inf')

        # Factor of safety against bolt yield
        FS_yield = self.mat.bolt_yield / sigma_bolt

        return {
            "bolt_load": F_bolt_total,
            "member_load": F_member,
            "bolt_stress": sigma_bolt,
            "separation_safety": FS_separation,
            "yield_safety": FS_yield,
            "load_factor": C,
            "k_bolt": self.k_bolt,
            "k_member": self.k_member,
        }

    def recommended_preload(self, preload_fraction: float = 0.75) -> float:
        """
        Calculate recommended preload as fraction of proof load.

        Typical practice: Preload = 0.75 * Proof load

        Args:
            preload_fraction: Fraction of proof strength (default: 0.75)

        Returns:
            Recommended preload in N
        """
        # Using yield strength as approximation for proof strength
        proof_load = self.mat.bolt_yield * self.stress_area

        F_preload = preload_fraction * proof_load

        return F_preload


def calculate_bearing_stress(load: float, bolt_diameter: float,
                             plate_thickness: float) -> float:
    """
    Calculate bearing stress on plate at bolt hole.

    σ_bearing = F / (d * t)

    Args:
        load: Bearing load in N
        bolt_diameter: Bolt diameter in mm
        plate_thickness: Plate thickness in mm

    Returns:
        Bearing stress in MPa
    """
    A_bearing = bolt_diameter * plate_thickness

    sigma_bearing = load / A_bearing

    return sigma_bearing


def calculate_shear_stress(load: float, stress_area: float,
                          num_shear_planes: int = 1) -> float:
    """
    Calculate shear stress in bolt.

    τ = F / (n * A_s)

    Args:
        load: Shear load in N
        stress_area: Thread stress area in mm^2
        num_shear_planes: Number of shear planes (default: 1 for single shear)

    Returns:
        Shear stress in MPa
    """
    tau = load / (num_shear_planes * stress_area)

    return tau


def eccentric_shear_load(load: float, eccentricity: float,
                         bolt_positions: np.ndarray) -> np.ndarray:
    """
    Calculate shear loads on bolts in an eccentrically loaded pattern.

    Uses elastic analysis (not ultimate strength analysis).

    Args:
        load: Applied shear load in N
        eccentricity: Distance from load to bolt pattern centroid in mm
        bolt_positions: Array of [x, y] bolt positions in mm (Nx2)

    Returns:
        Array of resultant loads on each bolt in N

    Note:
        This is a simplified elastic analysis. For design, consider
        plastic analysis or use AISC Design Guide.
    """
    n_bolts = len(bolt_positions)

    # Direct shear on each bolt
    F_direct = load / n_bolts

    # Calculate centroid
    centroid = np.mean(bolt_positions, axis=0)

    # Position vectors from centroid
    r = bolt_positions - centroid

    # Polar moment of inertia of bolt pattern
    J = np.sum(r[:, 0] ** 2 + r[:, 1] ** 2)

    # Moment
    M = load * eccentricity

    # Torsional shear forces (perpendicular to radius)
    F_torsion = np.zeros((n_bolts, 2))
    for i in range(n_bolts):
        r_mag = np.linalg.norm(r[i])
        if r_mag > 0:
            F_torsion_mag = M * r_mag / J
            # Force perpendicular to r
            F_torsion[i] = F_torsion_mag * np.array([-r[i, 1], r[i, 0]]) / r_mag

    # Direct shear (assuming load in x-direction)
    F_direct_vec = np.array([F_direct, 0])

    # Total force on each bolt
    F_total = np.linalg.norm(F_direct_vec + F_torsion, axis=1)

    return F_total


# TODO: Add functions for:
# - Fatigue analysis (Goodman diagram)
# - Gasketed joint analysis
# - Thermal effects on preload
# - Thread stripping analysis
# - Prying action in T-stub connections
