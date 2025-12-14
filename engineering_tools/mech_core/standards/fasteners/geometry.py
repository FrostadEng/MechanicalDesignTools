"""
mech_core/standards/fasteners/geometry.py
ISO Metric Thread Geometry Standards (ISO 261, ISO 724, ISO 898-1).
"""
from dataclasses import dataclass
import numpy as np
from mech_core.standards.units import ureg, Q_

@dataclass(frozen=True)
class MetricThread:
    """Immutable representation of a thread profile."""
    name: str
    nominal_dia: Q_  # d
    pitch: Q_        # P
    stress_area: Q_  # As
    
    @property
    def minor_diameter(self) -> Q_:
        """Calculate minor diameter (d3) for root area checks"""
        d_val = self.nominal_dia.to(ureg.mm).magnitude
        p_val = self.pitch.to(ureg.mm).magnitude
        # ISO Formula: d3 = d - 1.226869 * P
        d3 = d_val - (1.226869 * p_val)
        return d3 * ureg.mm

@dataclass(frozen=True)
class HexHead:
    """Immutable representation of a Hex Head (ISO 4014 / DIN 931)"""
    width_flats: Q_    # s (Wrench size)
    height: Q_         # k (Head height)

# --- THE ISO STANDARD DATABASE (COARSE SERIES) ---
# Source: ISO 261 (Threads) and ISO 4014 (Heads)
_ISO_DATA = {
    # Size: (Pitch_mm, StressArea_mm2, WidthFlats_mm, HeadHeight_mm)
    "M5":  (0.8,   14.2,  8.0,  3.5),
    "M6":  (1.0,   20.1,  10.0, 4.0),
    "M8":  (1.25,  36.6,  13.0, 5.3),
    "M10": (1.5,   58.0,  16.0, 6.4),
    "M12": (1.75,  84.3,  18.0, 7.5),  
    "M14": (2.0,   115.0, 21.0, 8.8),  
    "M16": (2.0,   157.0, 24.0, 10.0),
    "M20": (2.5,   245.0, 30.0, 12.5), 
    "M22": (2.5,   303.0, 34.0, 14.0),
    "M24": (3.0,   353.0, 36.0, 15.0),
    "M27": (3.0,   459.0, 41.0, 17.0),
    "M30": (3.5,   561.0, 46.0, 18.7),
    "M36": (4.0,   817.0, 55.0, 22.5),
    "M42": (4.5,   1120.0, 65.0, 26.0),
    "M48": (5.0,   1470.0, 75.0, 30.0),
    "M56": (5.5,   2030.0, 85.0, 35.0),
    "M64": (6.0,   2680.0, 95.0, 40.0)
}

def get_metric_thread(size: str) -> MetricThread:
    """
    Factory function to fetch safe, unit-aware thread objects.
    Args:
        size: "M20", "m20", "M20x2.5" (will parse "M20")
    """
    # Clean input: "M20x2.5" -> "M20"
    clean_size = size.split('x')[0].upper()
    
    if clean_size not in _ISO_DATA:
        # Fallback logic? No, structural bolts must be exact.
        available = ", ".join(_ISO_DATA.keys())
        raise ValueError(f"Thread '{size}' not found in ISO Coarse DB. Available: {available}")
    
    # Unpack tuple
    p, area, _, _ = _ISO_DATA[clean_size]
    
    # Extract diameter from name "M20" -> 20.0
    d_nom = float(clean_size[1:])
    
    return MetricThread(
        name=clean_size,
        nominal_dia=d_nom * ureg.mm,
        pitch=p * ureg.mm,
        stress_area=area * ureg.mm**2
    )

def get_hex_head(size: str) -> HexHead:
    clean_size = size.split('x')[0].upper()
    if clean_size not in _ISO_DATA:
        raise ValueError(f"Head dimensions for '{size}' not found.")
        
    _, _, s, k = _ISO_DATA[clean_size]
    return HexHead(
        width_flats=s * ureg.mm,
        height=k * ureg.mm
    )