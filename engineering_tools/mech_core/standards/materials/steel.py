"""
mech_core/standards/materials/steel.py
Structural steel material definitions (ASTM/CSA grades).
"""
from dataclasses import dataclass
from ...units import ureg, Q_

@dataclass(frozen=True)
class StructuralMaterial:
    name: str
    yield_strength: Q_    # Sy (Fy)
    ultimate_strength: Q_ # Sut (Fu)
    elastic_modulus: Q_   # E
    density: Q_           # rho

_STRUCTURAL_DB = {
    # USA
    "ASTM A36":   {"Sy": 250, "Sut": 400, "E": 200, "rho": 7850},
    "ASTM A992":  {"Sy": 345, "Sut": 450, "E": 200, "rho": 7850},

    # CANADA (The Good Stuff)
    "CSA G40.21 350W": {"Sy": 350, "Sut": 450, "E": 200, "rho": 7850},
    "CSA G40.21 300W": {"Sy": 300, "Sut": 450, "E": 200, "rho": 7850}, # Common for Angles/Channels
}

def get_material(name: str) -> StructuralMaterial:
    if name not in _STRUCTURAL_DB:
        raise ValueError(f"Material '{name}' not found.")
    data = _STRUCTURAL_DB[name]
    return StructuralMaterial(
        name=name,
        yield_strength=data["Sy"] * ureg.MPa,
        ultimate_strength=data["Sut"] * ureg.MPa,
        elastic_modulus=data["E"] * ureg.GPa,
        density=data["rho"] * (ureg.kg / ureg.meter**3)
    )
