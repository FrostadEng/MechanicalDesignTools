import json
import os
from mech_core.units import ureg, Q_

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "data", "aisc_shapes.json")

_SHAPE_DB = {}
_METRIC_MAP = {}

if os.path.exists(DB_PATH):
    with open(DB_PATH, 'r') as f:
        _SHAPE_DB = json.load(f)
        
    for key, data in _SHAPE_DB.items():
        if "name_metric" in data and data["name_metric"]:
            _METRIC_MAP[data["name_metric"]] = key

class SectionProperties:
    def __init__(self, data_dict):
        self._data = data_dict
        self.name = data_dict.get('name_imperial')
        self.metric_name = data_dict.get('name_metric')
        self.type = data_dict.get('type')
        
    def __getattr__(self, name):
        if name in self._data:
            val = self._data[name]
            if val is None: return None
            
            # ==========================================
            # AISC V16 METRIC UNIT SCALING
            # Based on AISC Database v16.0 Readme
            # ==========================================

            # --- GROUP 1: MOMENTS OF INERTIA (x 10^6 mm^4) ---
            if name in ['Ix', 'Iy', 'Iz', 'Iw', 'Sw1', 'Sw2', 'Sw3']:
                return (val * 1e6) * ureg.mm**4
            
            # --- GROUP 2: TORSIONAL CONSTANT J (x 10^3 mm^4) ---
            # Note: J is scaled differently than I in the metric table!
            if name == 'J':
                return (val * 1e3) * ureg.mm**4

            # --- GROUP 3: SECTION MODULI & STATICAL MOMENTS (x 10^3 mm^3) ---
            # 'C' is the HSS Torsional Constant (mm^3), not to be confused with warping Cw
            if name in ['Zx', 'Sx', 'Zy', 'Sy', 'Sz', 'Qf', 'Qw', 'C',
                        'SwA', 'SwB', 'SwC', 'SzA', 'SzB', 'SzC']:
                return (val * 1e3) * ureg.mm**3
            
            # --- GROUP 4: WARPING CONSTANT (x 10^9 mm^6) ---
            if name == 'Cw':
                return (val * 1e9) * ureg.mm**6
            
            # --- GROUP 5: AREAS (mm^2) ---
            if name in ['A', 'Wno']:
                return val * ureg.mm**2

            # --- GROUP 6: LENGTHS (mm) ---
            # 'ho' = Distance between flange centroids
            # 'rts' = Effective Radius of Gyration
            # 'PA', 'PB', 'PC', 'PD' = Perimeters (Length units, NOT Area)
            if name in [
                'd', 'bf', 'tf', 'tw', 'h', 'OD', 'ID', 'Ht', 'B', 'b', 't', 
                'kdes', 'kdet', 'k1', 'x', 'y', 'eo', 'xp', 'yp', 
                'rx', 'ry', 'rz', 'ro', 'rts', 'ho',
                'T', 'WGi', 'WGo', 
                'ddet', 'bfdet', 'twdet', 'twdet_2', 'tfdet', 'tnom', 'tdes',
                'zA', 'zB', 'zC', 'wA', 'wB', 'wC',
                'PA', 'PA2', 'PB', 'PC', 'PD'
            ]:
                return val * ureg.mm
            
            # --- GROUP 7: Linear Density (kg/m) ---
            if name == 'W':
                return val * (ureg.kg / ureg.meter)

            # --- GROUP 8: DIMENSIONLESS ---
            # tan_alpha, H (Flexural Constant), Slenderness Ratios
            # We return these as raw floats (no units)
            return val
            
        raise AttributeError(f"Section '{self.name}' has no property '{name}'")

    def __repr__(self):
        return f"<Section {self.name}>"

def get_section(callout: str) -> SectionProperties:
    key = callout.strip().upper()
    if key in _SHAPE_DB: return SectionProperties(_SHAPE_DB[key])
    if key in _METRIC_MAP: return SectionProperties(_SHAPE_DB[_METRIC_MAP[key]])
    
    key_swapped = key.replace('x', 'X')
    if key_swapped in _SHAPE_DB: return SectionProperties(_SHAPE_DB[key_swapped])
    
    raise ValueError(f"Shape '{callout}' not found.")