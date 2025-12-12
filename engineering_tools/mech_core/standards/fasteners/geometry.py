"""
mech_core/standards/fasteners/geometry.py
ISO Metric Thread Geometry Standards (ISO 68-1, ISO 261, ISO 4014)
"""
from dataclasses import dataclass
import numpy as np

from mech_core.units import ureg, Q_

@dataclass(frozen=True)
class MetricThread:
    """Immutable representation of a thread profile."""
    name: str
    nominal_dia: Q_  # [length]
    pitch: Q_        # [length]
    pitch_dia: Q_    # [length]
    minor_dia: Q_    # [length]
    
    @property
    def stress_area(self) -> Q_:
        """Calculates Tensile Stress Area (As) per ISO 898-1"""
        # As = (pi/4) * ((d2 + d3) / 2)^2
        d2 = self.pitch_dia
        d3 = self.minor_dia
        area = (np.pi / 4) * ((d2 + d3) / 2)**2
        return area

@dataclass(frozen=True)
class HexHead:
    """Immutable representation of a Hex Head (ISO 4014)"""
    width_flats: Q_    # s
    width_corners: Q_  # e
    height: Q_         # k

# --- THE DATABASE ---
# We define the raw data here, but we expose Objects, not Dicts.

_THREADS_DB = {
    "M6":  {"p": 1.0,  "d2": 5.350,  "d3": 4.917},
    "M8":  {"p": 1.25, "d2": 7.188,  "d3": 6.647},
    "M10": {"p": 1.5,  "d2": 9.026,  "d3": 8.376},
    "M12": {"p": 1.75, "d2": 10.863, "d3": 10.106},
    "M16": {"p": 2.0,  "d2": 14.701, "d3": 13.835},
}

_HEADS_DB = {
    "M6":  {"s": 10.0, "e": 11.55, "k": 4.0},
    "M8":  {"s": 13.0, "e": 15.01, "k": 5.3},
    "M10": {"s": 16.0, "e": 18.48, "k": 6.4},
    "M12": {"s": 18.0, "e": 20.78, "k": 7.5},
    "M16": {"s": 24.0, "e": 27.71, "k": 10.0},
}

def get_metric_thread(size: str) -> MetricThread:
    """Factory function to fetch safe, unit-aware thread objects."""
    if size not in _THREADS_DB:
        raise ValueError(f"Thread '{size}' not found in database.")
    
    data = _THREADS_DB[size]
    return MetricThread(
        name=size,
        nominal_dia=float(size[1:]) * ureg.mm, # Extracts '6' from 'M6'
        pitch=data["p"] * ureg.mm,
        pitch_dia=data["d2"] * ureg.mm,
        minor_dia=data["d3"] * ureg.mm
    )

def get_hex_head(size: str) -> HexHead:
    if size not in _HEADS_DB:
        raise ValueError(f"Head '{size}' not found.")
    data = _HEADS_DB[size]
    return HexHead(
        width_flats=data["s"] * ureg.mm,
        width_corners=data["e"] * ureg.mm,
        height=data["k"] * ureg.mm
    )