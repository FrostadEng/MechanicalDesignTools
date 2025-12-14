# mech_core/units.py
import pint

# The Single Source of Truth
ureg = pint.UnitRegistry()

# Define standard formats (optional but nice)
ureg.default_format = ".3f"

# The Quantity constructor (Standard naming convention)
Q_ = ureg.Quantity