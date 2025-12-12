"""
Helper functions for querying the AISC shapes database.

Provides utilities to filter and search through steel sections by type,
size, weight, and other properties.
"""

import json
import os
from typing import List, Optional, Dict, Any
from mech_core.units import ureg, Q_

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "data", "aisc_shapes.json")

_SHAPE_DB = {}

if os.path.exists(DB_PATH):
    with open(DB_PATH, 'r') as f:
        _SHAPE_DB = json.load(f)


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
