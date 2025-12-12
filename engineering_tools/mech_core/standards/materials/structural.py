"""
mech_core/standards/materials/structural.py
Common structural materials (ASTM/ASM).
"""
from dataclasses import dataclass
from mech_core.units import ureg, Q_

@dataclass(frozen=True)
class StructuralMaterial:
    name: str
    yield_strength: Q_    # Sy
    ultimate_strength: Q_ # Sut
    elastic_modulus: Q_   # E (Young's Modulus)
    density: Q_           # rho

# --- THE DATABASE ---
_STRUCTURAL_DB = {
    # Structural Steel (The most common plate material)
    "ASTM A36": {
        "Sy": 250, "Sut": 400, "E": 200, "rho": 7850
    },
    # Stainless Steel
    "SS 304": {
        "Sy": 215, "Sut": 505, "E": 193, "rho": 8000
    },
    # Aluminum (Robot end-effectors are often Al)
    "6061-T6": {
        "Sy": 276, "Sut": 310, "E": 68.9, "rho": 2700
    }
}

def get_material(name: str) -> StructuralMaterial:
    if name not in _STRUCTURAL_DB:
        raise ValueError(f"Material '{name}' not found in Structural DB.")
    
    data = _STRUCTURAL_DB[name]
    # Note units: Yield=MPa, E=GPa, Rho=kg/m^3
    return StructuralMaterial(
        name=name,
        yield_strength=data["Sy"] * ureg.MPa,
        ultimate_strength=data["Sut"] * ureg.MPa,
        elastic_modulus=data["E"] * ureg.GPa,
        density=data["rho"] * (ureg.kg / ureg.meter**3)
    )