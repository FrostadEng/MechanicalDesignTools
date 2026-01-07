from ..machines.subsystems.planning.parsers.dstv import DSTVData, DSTVFeature
from ....mech_core.components.members.aisc import get_section
from ....mech_core.standards.materials.steel import get_material, StructuralMaterial

class BeamEntity:
    def __init__(self, dstv_data: DSTVData):
        self.dstv_data = dstv_data
        self.name = dstv_data.filename
        
        # 1. Hydrate Physics from Mech_Core
        # Get Geometry (Web/Flange thickness)
        self.section = get_section(dstv_data.profile_code)
        
        # Get Material Properties (Melting Point, Density, etc.)
        # Default to A992 if not specified in DSTV, or map string to DB
        mat_name = "ASTM A992" if "992" in dstv_data.material_grade else "ASTM A36"
        self.material: StructuralMaterial = get_material(mat_name)

    def get_thickness_at_feature(self, feature: DSTVFeature) -> float:
        """
        Returns the thickness (mm) of the steel at the feature's location.
        """
        # DSTV Face Codes:
        # 'v' = Vorderseite (Front/Web)
        # 'h' = Hinterseite (Rear/Web)
        # 'o' = Oberseite (Top Flange)
        # 'u' = Unterseite (Bottom Flange)
        
        if feature.face in ['v', 'h']:
            # Return Web Thickness (tw)
            # Section props are Pint objects, convert to mm float
            return self.section.web_thickness.to("mm").magnitude
            
        elif feature.face in ['o', 'u']:
            # Return Flange Thickness (tf)
            return self.section.flange_thickness.to("mm").magnitude
            
        return 10.0 # Default fallback