from typing import List, Dict, Literal
from dataclasses import dataclass, field
from ..subsystems.planning.parsers.dstv import DSTVData, DSTVFeature
from .config import WINDOW_WIDTH, CLAMP_OVERLAP


@dataclass
class MachineCycle:
    """
    Represents a single machine operation cycle in the PCR41.

    Cycle Types:
    - PROCESS: Robot processes features within current window
    - SEVER: Robot performs vertical chop to bisect spanning feature
    - INDEX: Feeder advances beam to next window position
    """
    type: Literal["PROCESS", "SEVER", "INDEX"]
    window_start: float  # X-position of window start (mm)
    window_end: float    # X-position of window end (mm)
    features: List[DSTVFeature] = field(default_factory=list)  # For PROCESS
    sever_length: float = 0.0  # For SEVER (vertical chop length in mm)
    target_position: float = 0.0  # For INDEX (absolute feeder position in mm)

class Indexer:
    """
    The Brain. Transforms DSTV features into machine cycles using sliding window logic.

    Supports two modes:
    1. Legacy spatial clustering (group_features)
    2. Sliding window with bisection (plan_beam)
    """
    def __init__(self, window_width: float = WINDOW_WIDTH, overlap: float = CLAMP_OVERLAP, tolerance_mm: float = 1.0):
        """
        Initialize the indexer.

        Args:
            window_width: Processing window width in mm (default 200mm from config)
            overlap: Safety buffer at window boundaries in mm
            tolerance_mm: Spatial clustering tolerance for legacy mode
        """
        self.window_width = window_width
        self.overlap = overlap
        self.tolerance = tolerance_mm

    def group_features(self, beam_data: DSTVData) -> Dict[float, List[DSTVFeature]]:
        """
        Groups features that share the same X-Position (within tolerance).
        Returns a Dictionary: { x_pos_mm : [list_of_features] }
        """
        grouped = {}
        
        # Sort raw features by X
        sorted_features = sorted(beam_data.features, key=lambda f: f.x_pos)
        
        for feat in sorted_features:
            # Find an existing group close to this feature
            found_group = False
            for group_x in grouped.keys():
                if abs(feat.x_pos - group_x) < self.tolerance:
                    grouped[group_x].append(feat)
                    found_group = True
                    break
            
            if not found_group:
                # Create new group key
                grouped[feat.x_pos] = [feat]
                
        return grouped

    def get_optimized_plan(self, beam_data: DSTVData):
        """
        Returns a sorted list of tuples: (x_position, features_at_this_position)
        """
        groups = self.group_features(beam_data)
        # Return sorted by X position
        return sorted(groups.items())

    def plan_beam(self, beam_data: DSTVData) -> List[MachineCycle]:
        """
        Generate machine cycles using sliding window algorithm with bisection logic.

        Algorithm:
        1. Initialize window at X=0
        2. For each window position:
           - Identify features fully inside window
           - Identify features spanning window boundary
           - Generate PROCESS cycle for contained features
           - Generate PROCESS + SEVER + INDEX for spanning features
        3. Advance window and repeat

        Args:
            beam_data: Parsed DSTV data with features

        Returns:
            List of MachineCycle objects (PROCESS, SEVER, INDEX)
        """
        cycles = []
        window_start = 0.0

        # Sort features by X position for sequential processing
        sorted_features = sorted(beam_data.features, key=lambda f: f.x_pos)

        # Track which features have been processed (use list since DSTVFeature isn't hashable)
        processed_features = []

        while window_start < beam_data.length_mm:
            window_end = window_start + self.window_width

            # Get features in current window
            window_features = []
            spanning_features = []

            for feat in sorted_features:
                if feat in processed_features:
                    continue

                # Check if feature starts in current window
                if window_start <= feat.x_pos <= window_end:
                    # Calculate where feature ends
                    feature_end = feat.x_pos + feat.path_length

                    if feature_end <= window_end + self.overlap:
                        # Fully contained within window
                        window_features.append(feat)
                        processed_features.append(feat)
                    else:
                        # Spanning - extends beyond window boundary
                        spanning_features.append(feat)
                        processed_features.append(feat)

            # Generate cycles for this window
            if window_features or spanning_features:
                # PROCESS cycle for all features fully in window
                if window_features:
                    cycles.append(MachineCycle(
                        type="PROCESS",
                        window_start=window_start,
                        window_end=window_end,
                        features=window_features
                    ))

                # Handle spanning features with bisection
                for span_feat in spanning_features:
                    # PROCESS partial cut to window boundary
                    cycles.append(MachineCycle(
                        type="PROCESS",
                        window_start=window_start,
                        window_end=window_end,
                        features=[span_feat]
                    ))

                    # SEVER operation (vertical chop)
                    # Use profile_height if available, otherwise conservative default
                    sever_length = getattr(beam_data, 'profile_height', 300.0)
                    cycles.append(MachineCycle(
                        type="SEVER",
                        window_start=window_start,
                        window_end=window_end,
                        sever_length=sever_length
                    ))

                # INDEX to next window (with overlap for clamp positioning)
                next_window_start = window_end - self.overlap
                cycles.append(MachineCycle(
                    type="INDEX",
                    window_start=window_start,
                    window_end=window_end,
                    target_position=next_window_start
                ))

                window_start = next_window_start
            else:
                # No features in this window, advance
                window_start = window_end - self.overlap

            # Safety check: prevent infinite loop
            if window_start > beam_data.length_mm + self.window_width:
                break

        return cycles