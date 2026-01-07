"""
mech_core/standards/materials/steel.py
Structural steel material definitions (ASTM/CSA grades).
Includes Mechanical, Thermodynamic, and Surface Interaction properties.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from ..units import ureg, Q_

# ==========================================
# 1. THE DATA CLASSES
# ==========================================

@dataclass(frozen=True)
class SurfacePhysics:
    """
    Physical properties dependent on the surface condition.
    Crucial for Laser/Plasma interaction.
    """
    condition_name: str
    description: str
    absorptivity_1um: float  # For Fiber Laser (1064nm). Range 0.0 - 1.0
    emissivity: float        # For Thermal Radiation. Range 0.0 - 1.0

@dataclass(frozen=True)
class StructuralMaterial:
    name: str
    
    # --- Mechanical Properties (The "Statics") ---
    yield_strength: Q_    # Sy (Fy)
    ultimate_strength: Q_ # Sut (Fu)
    elastic_modulus: Q_   # E
    density: Q_           # rho
    
    # --- Thermodynamic Properties (The "Energy Balance") ---
    melting_point: Q_         # Tm
    specific_heat: Q_         # cp
    thermal_conductivity: Q_  # k
    latent_heat_fusion: Q_    # Lf
    
    # --- Surface Conditions (The "Interface") ---
    # A dictionary mapping condition names to Physics objects
    # e.g. material.surfaces['mill_scale'].absorptivity_1um
    surfaces: Dict[str, SurfacePhysics] = field(default_factory=dict)

    def get_surface(self, condition: str) -> SurfacePhysics:
        """Helper to safely fetch surface physics."""
        if condition not in self.surfaces:
            # Fallback to a generic 'clean' if specific condition missing
            if 'clean' in self.surfaces:
                return self.surfaces['clean']
            raise ValueError(f"Surface condition '{condition}' not defined for {self.name}")
        return self.surfaces[condition]

# ==========================================
# 2. THE DATABASE (Specific Data for Specific Alloys)
# ==========================================

# We define a "Base Steel" set of thermals to keep the DB clean, 
# but we will copy/override this for every single entry.
_BASE_THERMALS = {
    "Tm": 1510,   # degC
    "cp": 490,    # J/kg*K
    "k":  45,     # W/m*K
    "Lf": 272000  # J/kg
}

_STRUCTURAL_DB = {
    # --- USA GRADES ---
    "ASTM A36": {
        "mech": {"Sy": 250, "Sut": 400, "E": 200, "rho": 7850},
        "therm": _BASE_THERMALS.copy(), # A36 is standard
        "surfaces": {
            "mill_scale": {"abs": 0.70, "emis": 0.85, "desc": "Standard hot-rolled dark oxide"},
            "blast_cleaned": {"abs": 0.45, "emis": 0.30, "desc": "Silver-grey, shot blasted"},
            "light_rust": {"abs": 0.75, "emis": 0.90, "desc": "Orange/Brown oxidation"},
        }
    },
    
    "ASTM A992": {
        "mech": {"Sy": 345, "Sut": 450, "E": 200, "rho": 7850},
        # A992 has slight chemical differences (Vanadium/Columbium) 
        # that barely affect thermals, but we COULD change them here.
        "therm": _BASE_THERMALS.copy(), 
        "surfaces": {
            "mill_scale": {"abs": 0.65, "emis": 0.80, "desc": "Tighter, harder scale than A36"},
            "blast_cleaned": {"abs": 0.45, "emis": 0.30, "desc": "Standard clean"},
        }
    },

    # --- CANADA GRADES ---
    "CSA G40.21 350W": {
        "mech": {"Sy": 350, "Sut": 450, "E": 200, "rho": 7850},
        "therm": _BASE_THERMALS.copy(),
        "surfaces": {
            "mill_scale": {"abs": 0.70, "emis": 0.85, "desc": "Standard Can-Am scale"},
            "primed": {"abs": 0.92, "emis": 0.95, "desc": "Grey Zinc-Rich Primer (Laser absorbent)"},
        }
    },

    # --- WEATHERING STEEL (The Exception) ---
    "CSA G40.21 350A": { # Atmospheric Corrosion Resistant
        "mech": {"Sy": 350, "Sut": 480, "E": 200, "rho": 7890}, # Slightly denser due to Copper/Chromium
        "therm": {
             "Tm": 1505,   # Slightly lower melting point due to alloys
             "cp": 480,
             "k":  42,     # Lower conductivity due to alloying
             "Lf": 270000
        },
        "surfaces": {
            "patina": {"abs": 0.85, "emis": 0.95, "desc": "Stable protective rust layer"},
            "blast_cleaned": {"abs": 0.50, "emis": 0.35, "desc": "Clean weathering steel"},
        }
    }
}

# ==========================================
# 3. THE FACTORY
# ==========================================

def get_material(name: str) -> StructuralMaterial:
    if name not in _STRUCTURAL_DB:
        raise ValueError(f"Material '{name}' not found within internal DB.")
    
    raw = _STRUCTURAL_DB[name]
    m_data = raw["mech"]
    t_data = raw["therm"]
    s_data = raw["surfaces"]

    # Build the Surface Objects
    surface_map = {}
    for key, data in s_data.items():
        surface_map[key] = SurfacePhysics(
            condition_name=key,
            description=data["desc"],
            absorptivity_1um=data["abs"],
            emissivity=data["emis"]
        )

    return StructuralMaterial(
        name=name,
        # Mechanical (Multiplication works fine here because MPa is absolute)
        yield_strength=m_data["Sy"] * ureg.MPa,
        ultimate_strength=m_data["Sut"] * ureg.MPa,
        elastic_modulus=m_data["E"] * ureg.GPa,
        density=m_data["rho"] * (ureg.kg / ureg.meter**3),
        
        # Thermal Fix: Use ureg.Quantity() for Offset Units (degC)
        melting_point=ureg.Quantity(t_data["Tm"], ureg.degC), 
        
        # These are safe to multiply because they contain Delta Kelvin (units of slope)
        specific_heat=t_data["cp"] * ureg.J / (ureg.kg * ureg.kelvin),
        thermal_conductivity=t_data["k"] * ureg.watt / (ureg.meter * ureg.kelvin),
        latent_heat_fusion=t_data["Lf"] * ureg.J / ureg.kg,
        
        # Surfaces
        surfaces=surface_map
    )