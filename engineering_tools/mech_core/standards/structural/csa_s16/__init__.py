"""
CSA S16 - Canadian Steel Design Standard

This package contains code-specific validation logic for CSA S16.
"""
from .members import check_compressive_resistance, check_flexural_resistance

__all__ = ['check_compressive_resistance', 'check_flexural_resistance']
