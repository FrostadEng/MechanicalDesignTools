"""
mech_core/analysis/statics/section_properties.py

Geometric section property calculations from cross-section dimensions.

Supports the following standard shapes:
  Rectangular, Circular, Hollow Circular, I-Beam (W), Channel (C),
  T-Section, Angle (L), HSS Rectangular, HSS Square,
  Hollow Ellipse, Polygonal Tube.

All input dimensions are in millimetres (mm).
Returned properties are Pint quantities, duck-typing SectionProperties
from mech_core.components.members.aisc for use in FrameAnalysis.
"""

import math
from dataclasses import dataclass

from ...standards.units import ureg, Q_


# ---------------------------------------------------------------------------
# Result type  (duck-types aisc.SectionProperties)
# ---------------------------------------------------------------------------

@dataclass
class GeometricSection:
    """
    Cross-section properties computed from geometric dimensions.

    Duck-types SectionProperties so it can be passed directly to
    FrameAnalysis.add_beam().  Required attributes used by fea.py:
        .name  – str label
        .A     – area            (Pint, mm²)
        .Ix    – strong-axis I   (Pint, mm⁴)
        .Iy    – weak-axis I     (Pint, mm⁴)
        .J     – torsion const   (Pint, mm⁴)
    """
    name: str
    A:    Q_
    Ix:   Q_
    Iy:   Q_
    J:    Q_
    type: str = "CUSTOM"


# ---------------------------------------------------------------------------
# Shape parameter catalog
# Each entry: shape_name → {param_key: (ui_label, unit_suffix, default_mm)}
# The order of keys defines the form row order.
# ---------------------------------------------------------------------------

SHAPE_PARAMS: dict = {
    "Rectangular": {
        "b": ("Width b",           "mm", 100.0),
        "h": ("Depth h",           "mm", 200.0),
    },
    "Circular": {
        "d": ("Diameter d",        "mm", 100.0),
    },
    "Hollow Circular": {
        "OD": ("Outer Diameter OD", "mm", 120.0),
        "ID": ("Inner Diameter ID", "mm",  80.0),
    },
    "I-Beam (W)": {
        "d":  ("Total Depth d",        "mm", 200.0),
        "bf": ("Flange Width bf",       "mm", 150.0),
        "tf": ("Flange Thickness tf",   "mm",  10.0),
        "tw": ("Web Thickness tw",      "mm",   6.0),
    },
    "Channel (C)": {
        "d":  ("Total Depth d",        "mm", 200.0),
        "bf": ("Flange Width bf",       "mm",  75.0),
        "tf": ("Flange Thickness tf",   "mm",   9.0),
        "tw": ("Web Thickness tw",      "mm",   6.0),
    },
    "T-Section": {
        "d":  ("Total Depth d",        "mm", 150.0),
        "bf": ("Flange Width bf",       "mm", 120.0),
        "tf": ("Flange Thickness tf",   "mm",  10.0),
        "tw": ("Stem Thickness tw",     "mm",   7.0),
    },
    "Angle (L)": {
        "b1": ("Horizontal Leg b1",    "mm", 100.0),
        "b2": ("Vertical Leg b2",      "mm", 100.0),
        "t":  ("Thickness t",          "mm",   8.0),
    },
    "HSS Rectangular": {
        "b": ("Width b",               "mm", 150.0),
        "h": ("Depth h",               "mm", 200.0),
        "t": ("Wall Thickness t",      "mm",   8.0),
    },
    "HSS Square": {
        "b": ("Side b",                "mm", 150.0),
        "t": ("Wall Thickness t",      "mm",   8.0),
    },
    "Hollow Ellipse": {
        "a": ("Semi-major axis a",     "mm", 100.0),
        "b": ("Semi-minor axis b",     "mm",  60.0),
        "t": ("Wall Thickness t",      "mm",   6.0),
    },
    "Polygonal Tube": {
        "n": ("Number of Sides n",     "",    6.0),
        "R": ("Outer Circumradius R",  "mm",  80.0),
        "t": ("Wall Thickness t",      "mm",   6.0),
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wrap(name: str, A: float, Ix: float, Iy: float, J: float) -> GeometricSection:
    """Attach Pint units (mm² / mm⁴) and return a GeometricSection."""
    return GeometricSection(
        name=name,
        A=A  * ureg.mm**2,
        Ix=Ix * ureg.mm**4,
        Iy=Iy * ureg.mm**4,
        J=J  * ureg.mm**4,
    )


def _rect_J(b: float, h: float) -> float:
    """
    St. Venant torsion constant for a solid rectangle (all dims in mm).

    Uses the Timoshenko series approximation (12 terms of the odd-harmonic
    series), accurate to better than 0.1 % for any aspect ratio.
    Automatically uses the longer dimension as b.
    """
    if h > b:
        b, h = h, b
    return (
        b * h**3 / 3
        * (1 - (192 * h / (math.pi**5 * b))
           * sum(math.tanh(math.pi * b / (2 * h * n)) / n**5
                 for n in range(1, 24, 2)))
    )


def _poly_I(n: int, Rc: float) -> float:
    """
    Second moment of area I_x = I_y for a solid regular n-gon
    with circumradius Rc, computed by signed-triangle fan from the centroid
    (origin).  Result in mm⁴ when Rc is in mm.

    Validated against known results:
      n=4 (square, Rc=R):  I = R⁴/3        (= side⁴/12 with side=R√2)
      n=6 (hexagon, Rc=R): I = 5√3/16 · R⁴
      n→∞ (circle, Rc=R):  I → πR⁴/4
    """
    theta0 = 2.0 * math.pi / n
    I = 0.0
    for k in range(n):
        th1 = k * theta0
        th2 = (k + 1) * theta0
        x1, y1 = Rc * math.cos(th1), Rc * math.sin(th1)
        x2, y2 = Rc * math.cos(th2), Rc * math.sin(th2)
        det = abs(x1 * y2 - x2 * y1)
        I += det * (y1**2 + y1 * y2 + y2**2) / 12.0
    return I


# ---------------------------------------------------------------------------
# Shape calculators (all inputs in mm)
# ---------------------------------------------------------------------------

def rectangular(b: float, h: float) -> GeometricSection:
    """Solid rectangular cross-section.  b = width, h = depth (strong axis)."""
    return _wrap(
        f"Rect {b:.0f}×{h:.0f}",
        A=b * h,
        Ix=b * h**3 / 12.0,
        Iy=h * b**3 / 12.0,
        J=_rect_J(b, h),
    )


def circular(d: float) -> GeometricSection:
    """Solid circular cross-section.  d = diameter."""
    r = d / 2.0
    return _wrap(
        f"Circle Ø{d:.0f}",
        A=math.pi * r**2,
        Ix=math.pi * r**4 / 4.0,
        Iy=math.pi * r**4 / 4.0,
        J=math.pi * r**4 / 2.0,   # J = Ip = Ix + Iy for circle
    )


def hollow_circular(OD: float, ID: float) -> GeometricSection:
    """Hollow circular section (pipe / tube).  OD = outer diameter, ID = inner diameter."""
    return _wrap(
        f"Pipe Ø{OD:.0f}×{ID:.0f}",
        A=math.pi * (OD**2 - ID**2) / 4.0,
        Ix=math.pi * (OD**4 - ID**4) / 64.0,
        Iy=math.pi * (OD**4 - ID**4) / 64.0,
        J=math.pi * (OD**4 - ID**4) / 32.0,
    )


def i_beam(d: float, bf: float, tf: float, tw: float) -> GeometricSection:
    """
    Doubly-symmetric I-section (W-shape).
    d  = total depth, bf = flange width,
    tf = flange thickness, tw = web thickness.
    """
    hw = d - 2.0 * tf
    return _wrap(
        f"I {d:.0f}×{bf:.0f}",
        A=bf * d - (bf - tw) * hw,
        Ix=(bf * d**3 - (bf - tw) * hw**3) / 12.0,
        Iy=(2.0 * tf * bf**3 + hw * tw**3) / 12.0,
        J=(2.0 * bf * tf**3 + hw * tw**3) / 3.0,
    )


def channel(d: float, bf: float, tf: float, tw: float) -> GeometricSection:
    """
    C-channel (symmetric about horizontal centroidal axis).
    d  = total depth, bf = flange width,
    tf = flange thickness, tw = web thickness.

    Iy is computed about the centroidal vertical axis (not the web back-face).
    """
    hw = d - 2.0 * tf
    A  = 2.0 * bf * tf + hw * tw

    Ix = (tw * d**3 / 12.0
          + 2.0 * (bf * tf**3 / 12.0
                   + bf * tf * (d / 2.0 - tf / 2.0)**2))

    # Centroid measured from back face of web
    x_bar = (bf**2 * tf + tw**2 * hw / 2.0) / A

    Iy = (tw**3 * hw / 12.0 + tw * hw * (tw / 2.0 - x_bar)**2
          + 2.0 * (bf**3 * tf / 12.0 + bf * tf * (bf / 2.0 - x_bar)**2))

    J = (2.0 * bf * tf**3 + hw * tw**3) / 3.0
    return _wrap(f"C {d:.0f}×{bf:.0f}", A=A, Ix=Ix, Iy=Iy, J=J)


def t_section(d: float, bf: float, tf: float, tw: float) -> GeometricSection:
    """
    T-section (flange on top, stem downward).
    d  = total depth, bf = flange width,
    tf = flange thickness, tw = stem thickness.
    """
    hs = d - tf          # stem height
    A  = bf * tf + hs * tw

    # Centroid measured from top of flange
    y_bar = (bf * tf * (tf / 2.0) + hs * tw * (tf + hs / 2.0)) / A

    Ix = (bf  * tf**3 / 12.0 + bf  * tf  * (y_bar - tf / 2.0)**2
          + tw * hs**3 / 12.0 + tw  * hs  * (tf + hs / 2.0 - y_bar)**2)
    Iy = tf * bf**3 / 12.0 + hs * tw**3 / 12.0
    J  = (bf * tf**3 + hs * tw**3) / 3.0
    return _wrap(f"T {d:.0f}×{bf:.0f}", A=A, Ix=Ix, Iy=Iy, J=J)


def angle(b1: float, b2: float, t: float) -> GeometricSection:
    """
    Equal or unequal leg angle (L-section).
    b1 = horizontal leg length, b2 = vertical leg length,
    t  = uniform thickness.

    Ix / Iy are about the centroidal axes (not the principal axes).
    J uses the open thin-walled approximation.
    """
    # Decompose: horizontal leg (b1 × t) + vertical stub (t × (b2-t))
    A_h = b1 * t
    A_v = t * (b2 - t)
    A   = A_h + A_v

    xc_h, yc_h = b1 / 2.0, t / 2.0
    xc_v, yc_v = t / 2.0, t + (b2 - t) / 2.0

    x_bar = (A_h * xc_h + A_v * xc_v) / A
    y_bar = (A_h * yc_h + A_v * yc_v) / A

    Ix = (b1 * t**3    / 12.0 + A_h * (yc_h - y_bar)**2
          + t * (b2-t)**3 / 12.0 + A_v * (yc_v - y_bar)**2)
    Iy = (t  * b1**3    / 12.0 + A_h * (xc_h - x_bar)**2
          + (b2-t) * t**3 / 12.0 + A_v * (xc_v - x_bar)**2)
    J  = (b1 * t**3 + (b2 - t) * t**3) / 3.0
    return _wrap(f"L {b1:.0f}×{b2:.0f}×{t:.0f}", A=A, Ix=Ix, Iy=Iy, J=J)


def hss_rectangular(b: float, h: float, t: float) -> GeometricSection:
    """
    HSS rectangular (or square) tube.
    b = width, h = depth, t = wall thickness.

    J uses the Bredt closed thin-walled formula:
        J = 4·A_m² · t / p_m
    where A_m and p_m are the area and perimeter of the median-line rectangle.
    """
    bi, hi = b - 2.0 * t, h - 2.0 * t
    A_m    = (b - t) * (h - t)
    perim_m = 2.0 * ((b - t) + (h - t))
    return _wrap(
        f"HSS {b:.0f}×{h:.0f}×{t:.0f}",
        A=b * h - bi * hi,
        Ix=(b * h**3 - bi * hi**3) / 12.0,
        Iy=(h * b**3 - hi * bi**3) / 12.0,
        J=4.0 * A_m**2 * t / perim_m,
    )


def hollow_ellipse(a: float, b: float, t: float) -> GeometricSection:
    """
    Hollow elliptical section.
    a = semi-major axis, b = semi-minor axis, t = wall thickness.

    J uses the Bredt formula with Ramanujan's perimeter approximation
    for the median-line ellipse.
    """
    ai, bi = a - t, b - t
    a_m, b_m = a - t / 2.0, b - t / 2.0
    A_m = math.pi * a_m * b_m
    # Ramanujan's second approximation for ellipse perimeter
    h_r = ((a_m - b_m) / (a_m + b_m))**2
    perim_m = (math.pi * (a_m + b_m)
               * (1.0 + 3.0 * h_r / (10.0 + math.sqrt(4.0 - 3.0 * h_r))))
    return _wrap(
        f"Ellipse {a:.0f}×{b:.0f}×{t:.0f}",
        A=math.pi * (a * b - ai * bi),
        Ix=math.pi * (a * b**3 - ai * bi**3) / 4.0,
        Iy=math.pi * (b * a**3 - bi * ai**3) / 4.0,
        J=4.0 * A_m**2 * t / perim_m,
    )


def polygonal_tube(n: int, R: float, t: float) -> GeometricSection:
    """
    Regular n-sided polygonal tube.
    n = number of sides, R = outer circumradius, t = wall thickness.

    Wall thickness is measured perpendicular to each face; the inner polygon
    has apothem = outer_apothem − t.

    I computed via signed-triangle fan (_poly_I); J via Bredt formula on
    the median-line polygon.
    """
    a_out = R * math.cos(math.pi / n)
    a_in  = max(a_out - t, 1e-6)
    R_in  = a_in / math.cos(math.pi / n)

    sin2 = math.sin(2.0 * math.pi / n)
    A_out = n * R**2   * sin2 / 2.0
    A_in  = n * R_in**2 * sin2 / 2.0

    a_m     = a_out - t / 2.0
    tan_pn  = math.tan(math.pi / n)
    A_m     = n * a_m**2 * tan_pn
    perim_m = 2.0 * n * a_m * tan_pn

    Ix = _poly_I(n, R) - _poly_I(n, R_in)
    return _wrap(
        f"Poly{n} R{R:.0f}×{t:.0f}",
        A=A_out - A_in,
        Ix=Ix,
        Iy=Ix,   # I_x = I_y for any regular polygon (rotational symmetry ≥ 3)
        J=4.0 * A_m**2 * t / perim_m,
    )


# ---------------------------------------------------------------------------
# Dispatch table + public entry point
# ---------------------------------------------------------------------------

_CALCULATORS = {
    "Rectangular":     lambda p: rectangular(p["b"], p["h"]),
    "Circular":        lambda p: circular(p["d"]),
    "Hollow Circular": lambda p: hollow_circular(p["OD"], p["ID"]),
    "I-Beam (W)":      lambda p: i_beam(p["d"], p["bf"], p["tf"], p["tw"]),
    "Channel (C)":     lambda p: channel(p["d"], p["bf"], p["tf"], p["tw"]),
    "T-Section":       lambda p: t_section(p["d"], p["bf"], p["tf"], p["tw"]),
    "Angle (L)":       lambda p: angle(p["b1"], p["b2"], p["t"]),
    "HSS Rectangular": lambda p: hss_rectangular(p["b"], p["h"], p["t"]),
    "HSS Square":      lambda p: hss_rectangular(p["b"], p["b"], p["t"]),
    "Hollow Ellipse":  lambda p: hollow_ellipse(p["a"], p["b"], p["t"]),
    "Polygonal Tube":  lambda p: polygonal_tube(int(round(p["n"])), p["R"], p["t"]),
}


def from_dimensions(shape: str, params: dict) -> GeometricSection:
    """
    Compute section properties from a shape name and parameter dictionary.

    Args:
        shape:  One of the keys in SHAPE_PARAMS (e.g. ``"I-Beam (W)"``).
        params: Mapping of parameter keys to float values in mm
                (e.g. ``{"d": 200, "bf": 150, "tf": 10, "tw": 6}``).
                For "Polygonal Tube", ``"n"`` is the integer side count.

    Returns:
        GeometricSection with Pint-unit A, Ix, Iy, J.

    Raises:
        ValueError: If shape is unrecognised.
    """
    calc = _CALCULATORS.get(shape)
    if calc is None:
        raise ValueError(f"Unknown section shape: {shape!r}")
    return calc(params)
