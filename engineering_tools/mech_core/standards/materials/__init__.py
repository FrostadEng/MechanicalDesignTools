"""
mech_core/standards/materials

Material definitions and inventory management for structural engineering.
"""

# Import from new modular structure
from .steel import StructuralMaterial, get_material
from .concrete import ConcreteMaterial, get_concrete
from .inventory import stock

# Public API - maintains backward compatibility
__all__ = [
    'StructuralMaterial',
    'get_material',
    'ConcreteMaterial',
    'get_concrete',
    'stock',
]
