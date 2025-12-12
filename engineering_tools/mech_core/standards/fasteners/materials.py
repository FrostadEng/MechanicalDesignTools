"""
mech_core/standards/fasteners/materials.py
ISO 898-1 Mechanical Properties for Fasteners
"""
from dataclasses import dataclass
from mech_core.units import ureg, Q_

@dataclass(frozen=True)
class BoltMaterial:
    """Immutable representation of Fastener Material Properties"""
    name: str
    proof_strength: Q_    # Sp
    yield_strength: Q_    # Sy
    tensile_strength: Q_  # Sut

_MAT_DB = {
    "8.8":  {"Sp": 600, "Sy": 640, "Sut": 800},
    "10.9": {"Sp": 830, "Sy": 900, "Sut": 1000},
    "12.9": {"Sp": 970, "Sy": 1100, "Sut": 1200},
}

def get_iso_property_class(name: str) -> BoltMaterial:
    if name not in _MAT_DB:
        raise ValueError(f"Property Class '{name}' not found.")
    
    data = _MAT_DB[name]
    return BoltMaterial(
        name=name,
        proof_strength=data["Sp"] * ureg.MPa,
        yield_strength=data["Sy"] * ureg.MPa,
        tensile_strength=data["Sut"] * ureg.MPa
    )