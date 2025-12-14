# AISC Shape Query Examples

This document shows how to use the query functions to search and filter AISC steel sections.

## Basic Usage

```python
from mech_core.components.members.aisc import (
    get_section,
    get_shapes_by_type,
    get_shapes_in_range,
    get_lightest_shape,
    get_available_types,
    search_shapes
)

# Get all W-shapes sorted by weight (lightest first)
w_shapes = get_shapes_by_type("W", sort_by="W")
print(w_shapes[:5])  # First 5 lightest W-shapes
# Output: ['W4X13', 'W5X16', 'W6X9', 'W6X8.5', 'W8X10']

# Get all C-channels sorted by area
c_channels = get_shapes_by_type("C", sort_by="A")

# Get all available shape types
types = get_available_types()
print(types)
# Output: ['C', 'HSS', 'L', 'MC', 'W', ...]
```

## Filtering by Property Range

```python
# Get W-shapes with depth between 200-300mm
medium_depth_w = get_shapes_in_range(
    shape_type="W",
    property_name="d",
    min_value=200,
    max_value=300,
    sort_by="W"
)

# Get C-channels with weight less than 20 kg/m
light_channels = get_shapes_in_range(
    shape_type="C",
    property_name="W",
    max_value=20
)

# Get W-shapes with section modulus Zx > 1000e3 mm³
strong_beams = get_shapes_in_range(
    shape_type="W",
    property_name="Zx",
    min_value=1000
)
```

## Finding the Lightest Adequate Section

```python
# Find the lightest W-shape with Zx >= 1500e3 mm³
lightest = get_lightest_shape(
    shape_type="W",
    property_name="Zx",
    min_value=1500
)
print(f"Lightest adequate section: {lightest}")

# Find the lightest C-channel with area >= 2000 mm²
lightest_channel = get_lightest_shape(
    shape_type="C",
    property_name="A",
    min_value=2000
)
```

## Searching by Name Pattern

```python
# Search for all W8 shapes
w8_shapes = search_shapes("W8", limit=10)
print(w8_shapes)
# Output: ['W8X10', 'W8X13', 'W8X15', 'W8X18', ...]

# Search for shapes with "X20" in the name, C-type only
heavy_channels = search_shapes("X20", shape_type="C")
# Output: ['C12X20.7', 'C15X33.9', ...]
```

## Integration with Design Scripts

```python
from mech_core.components.members.aisc import get_section, get_shapes_by_type
from mech_core.analysis.columns import calculate_compressive_strength

# Design example: Find adequate column
required_capacity = 100  # kN
column_height = 3.0 * ureg.meter
steel = get_material("ASTM A36")

# Iterate through W-shapes from lightest to heaviest
for shape_name in get_shapes_by_type("W", sort_by="W"):
    section = get_section(shape_name)
    result = calculate_compressive_strength(section, steel, column_height)

    if result['Pu_capacity'].magnitude >= required_capacity:
        print(f"Selected: {shape_name}")
        break
```

## Available Properties for Filtering

Common properties you can use for `property_name`, `sort_by`:

### Geometric Properties
- `d` - Depth (mm)
- `bf` - Flange width (mm)
- `tw` - Web thickness (mm)
- `tf` - Flange thickness (mm)
- `A` - Cross-sectional area (mm²)

### Section Properties
- `W` - Weight per unit length (kg/m)
- `Ix`, `Iy` - Moments of inertia (mm⁴ × 10⁶)
- `Sx`, `Sy` - Elastic section moduli (mm³ × 10³)
- `Zx`, `Zy` - Plastic section moduli (mm³ × 10³)
- `rx`, `ry` - Radius of gyration (mm)
- `J` - Torsional constant (mm⁴ × 10³)

Note: Values in the JSON database are scaled. The query functions work with raw database values, but when you use `get_section()`, the values are automatically scaled and have units attached.
