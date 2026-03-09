"""
PCR41 Machine Configuration

Defines physical limits, transition costs, and operational parameters
for the PCR41 beam processing machine.
"""

# ==========================================
# Window Geometry (mm)
# ==========================================

#: Processing window width - features larger than this must be bisected
WINDOW_WIDTH = 200.0

#: Safety buffer at window boundaries for clamp positioning
CLAMP_OVERLAP = 50.0


# ==========================================
# Face-to-Face Transition Penalties (seconds)
# ==========================================

#: Time penalties for robot TCP reorientation when switching beam faces
#: The robot must rotate its end-effector when moving between:
#: - v: Front web (vertical face)
#: - o: Top flange (oben - German for "up")
#: - u: Bottom flange (unten - German for "down")
#: - h: Rear web (hinten - German for "back")
TRANSITION_COSTS = {
    "v": {"v": 0.0, "o": 1.5, "u": 1.5, "h": 2.5},  # Web to others
    "o": {"v": 1.5, "o": 0.0, "u": 4.0, "h": 1.5},  # Top to Bottom is slow (4.0s)
    "u": {"v": 1.5, "o": 4.0, "u": 0.0, "h": 1.5},  # Bottom to Top is slow (4.0s)
    "h": {"v": 2.5, "o": 1.5, "u": 1.5, "h": 0.0}   # Rear
}


# ==========================================
# Default Process Parameters
# ==========================================

#: Default material grade if DSTV parsing fails
DEFAULT_MATERIAL = "ASTM A36"

#: Default surface condition for laser absorption calculations
DEFAULT_SURFACE = "mill_scale"

#: Typical kerf width for fiber laser cutting (mm)
DEFAULT_KERF_MM = 1.5

#: Conservative process efficiency for laser cutting
DEFAULT_PROCESS_EFFICIENCY = 0.35


# ==========================================
# Feeder Limits
# ==========================================

#: Maximum feeder indexing speed (mm/s)
MAX_FEEDER_SPEED_MM_S = 500.0

#: Feeder acceleration (mm/s²)
FEEDER_ACCEL_MM_S2 = 200.0


# ==========================================
# Robot Safe Positions
# ==========================================

#: Robot safe Z height - high above processing window (mm)
ROBOT_SAFE_Z = 500.0
