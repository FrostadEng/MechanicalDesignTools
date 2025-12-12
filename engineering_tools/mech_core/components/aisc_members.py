"""
AISC Steel Section Database and Query Utilities

Provides access to AISC steel shapes (W, C, L, HSS, etc.) with property lookups
and filtering capabilities. Includes automatic unit scaling per AISC Database v16.0.
"""

import json
import os
from typing import List, Optional
from mech_core.units import ureg, Q_

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "../standards/materials", "aisc_shapes.json")

_SHAPE_DB = {}
_METRIC_MAP = {}

if os.path.exists(DB_PATH):
    with open(DB_PATH, 'r') as f:
        _SHAPE_DB = json.load(f)

    for key, data in _SHAPE_DB.items():
        if "name_metric" in data and data["name_metric"]:
            _METRIC_MAP[data["name_metric"]] = key


# ============================================================================
# SECTION PROPERTIES CLASS
# ============================================================================

class SectionProperties:
    """
    AISC steel section with automatic unit scaling.

    Properties are accessed as attributes (e.g., section.Zx, section.rx)
    and automatically scaled with Pint units per AISC Database v16.0.
    """

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


# ============================================================================
# SECTION LOOKUP FUNCTIONS
# ============================================================================

def get_section(callout: str) -> SectionProperties:
    """
    Retrieve a steel section by name.

    Args:
        callout: Section name (e.g., "W12X26", "C8X18.75", "HSS6X6X1/4")
                 Accepts both imperial and metric names

    Returns:
        SectionProperties object with unit-scaled properties

    Example:
        >>> section = get_section("W12X26")
        >>> print(section.Zx)  # Plastic section modulus with units
        >>> print(section.d)   # Depth with units
    """
    key = callout.strip().upper()
    if key in _SHAPE_DB: return SectionProperties(_SHAPE_DB[key])
    if key in _METRIC_MAP: return SectionProperties(_SHAPE_DB[_METRIC_MAP[key]])

    key_swapped = key.replace('x', 'X')
    if key_swapped in _SHAPE_DB: return SectionProperties(_SHAPE_DB[key_swapped])

    raise ValueError(f"Shape '{callout}' not found.")


# ============================================================================
# QUERY FUNCTIONS
# ============================================================================

def get_shapes_by_type(shape_type: str, sort_by: str = "W") -> List[str]:
    """
    Get all shape names of a specific type.

    Args:
        shape_type: The shape type (e.g., "W", "C", "L", "HSS", "WT", "MC", "S")
        sort_by: Property to sort by (default: "W" for weight)
                 Common options: "W", "A", "Zx", "Ix", "d"

    Returns:
        List of shape names sorted by the specified property

    Example:
        >>> get_shapes_by_type("W")  # All W-shapes sorted by weight
        ['W4X13', 'W5X16', 'W6X9', ...]

        >>> get_shapes_by_type("C", sort_by="A")  # All C-channels sorted by area
        ['C3X3.5', 'C3X4.1', ...]
    """
    shapes = []

    for name, data in _SHAPE_DB.items():
        if data.get("type") == shape_type:
            sort_value = data.get(sort_by, 0)
            if sort_value is None:
                sort_value = 0
            shapes.append((name, sort_value))

    # Sort by the property value
    shapes.sort(key=lambda x: x[1])

    return [name for name, _ in shapes]


def get_shapes_in_range(
    shape_type: str,
    property_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    sort_by: str = "W"
) -> List[str]:
    """
    Get shapes of a specific type within a property range.

    Args:
        shape_type: The shape type (e.g., "W", "C", "L")
        property_name: Property to filter by (e.g., "W", "A", "d", "Zx")
        min_value: Minimum value (inclusive), None for no minimum
        max_value: Maximum value (inclusive), None for no maximum
        sort_by: Property to sort results by (default: "W")

    Returns:
        List of shape names matching the criteria

    Example:
        >>> # Get W-shapes with depth between 200-300mm
        >>> get_shapes_in_range("W", "d", min_value=200, max_value=300)

        >>> # Get C-channels with weight less than 20 kg/m
        >>> get_shapes_in_range("C", "W", max_value=20)
    """
    shapes = []

    for name, data in _SHAPE_DB.items():
        if data.get("type") != shape_type:
            continue

        value = data.get(property_name)
        if value is None:
            continue

        # Check range
        if min_value is not None and value < min_value:
            continue
        if max_value is not None and value > max_value:
            continue

        sort_value = data.get(sort_by, 0)
        if sort_value is None:
            sort_value = 0
        shapes.append((name, sort_value))

    # Sort by the property value
    shapes.sort(key=lambda x: x[1])

    return [name for name, _ in shapes]


def get_lightest_shape(
    shape_type: str,
    property_name: str,
    min_value: float
) -> Optional[str]:
    """
    Get the lightest shape of a type that meets a minimum property requirement.

    Args:
        shape_type: The shape type (e.g., "W", "C")
        property_name: Property that must meet minimum (e.g., "Zx", "A", "Ix")
        min_value: Minimum required value

    Returns:
        Name of the lightest shape meeting the requirement, or None if none found

    Example:
        >>> # Find lightest W-shape with Zx >= 1000e3 mm³
        >>> get_lightest_shape("W", "Zx", 1000)
        'W14X26'
    """
    candidates = get_shapes_in_range(
        shape_type=shape_type,
        property_name=property_name,
        min_value=min_value,
        sort_by="W"
    )

    return candidates[0] if candidates else None


def get_available_types() -> List[str]:
    """
    Get all available shape types in the database.

    Returns:
        List of unique shape types

    Example:
        >>> get_available_types()
        ['W', 'C', 'L', 'HSS', 'WT', 'MC', 'S', ...]
    """
    types = set()
    for data in _SHAPE_DB.values():
        shape_type = data.get("type")
        if shape_type:
            types.add(shape_type)

    return sorted(list(types))


def search_shapes(
    name_pattern: str = "",
    shape_type: Optional[str] = None,
    limit: int = 10
) -> List[str]:
    """
    Search for shapes by name pattern and/or type.

    Args:
        name_pattern: Pattern to match in shape name (case-insensitive)
        shape_type: Optional type filter
        limit: Maximum number of results to return

    Returns:
        List of matching shape names

    Example:
        >>> search_shapes("W8", limit=5)
        ['W8X10', 'W8X13', 'W8X15', 'W8X18', 'W8X21']

        >>> search_shapes("X20", shape_type="C")
        ['C12X20.7', 'C15X33.9', ...]
    """
    pattern = name_pattern.upper()
    results = []

    for name, data in _SHAPE_DB.items():
        if shape_type and data.get("type") != shape_type:
            continue

        if pattern in name.upper():
            results.append(name)

        if len(results) >= limit:
            break

    return results
