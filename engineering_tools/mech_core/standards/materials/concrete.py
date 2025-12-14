"""
mech_core/standards/materials/concrete.py
Concrete material definitions and properties.
"""
from dataclasses import dataclass
from ..units import ureg, Q_

@dataclass(frozen=True)
class ConcreteMaterial:
    name: str
    fc_prime: Q_  # Compressive Strength (e.g., 25 MPa)
    phi_c: float = 0.65 # CSA A23.3 Resistance Factor

def get_concrete(fc_mpa: float) -> ConcreteMaterial:
    """Factory for concrete (e.g., get_concrete(30) -> 30 MPa Concrete)"""
    return ConcreteMaterial(
        name=f"Concrete {fc_mpa}MPa",
        fc_prime=fc_mpa * ureg.MPa
    )
