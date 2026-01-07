"""
Unit tests for WindowIndexer sliding window algorithm.

Tests verify:
- Single window beam produces minimal cycles
- Long beams produce multiple INDEX cycles
- Spanning features trigger SEVER operations
- Empty beams return empty cycle list
"""

import pytest
from ..core.machines.PCR41.indexer import Indexer, MachineCycle
from ..core.machines.subsystems.planning.parsers.dstv import DSTVData, DSTVFeature


def test_single_window_beam():
    """Beam shorter than window should produce single PROCESS cycle."""
    beam = DSTVData(
        filename="short_beam.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=150.0,
        features=[
            DSTVFeature("HOLE", "v", 50.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 100.0, 150.0, diameter=22.0),
        ]
    )

    indexer = Indexer(window_width=200.0)
    cycles = indexer.plan_beam(beam)

    # Should have PROCESS cycle but no INDEX needed (beam fits in one window)
    assert len(cycles) >= 1, "Should have at least one cycle"

    process_cycles = [c for c in cycles if c.type == "PROCESS"]
    assert len(process_cycles) >= 1, "Should have PROCESS cycle"
    assert len(process_cycles[0].features) == 2, "Should process both features"


def test_long_beam_multiple_windows():
    """Beam longer than window should produce multiple INDEX cycles."""
    beam = DSTVData(
        filename="long_beam.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=1000.0,
        features=[
            DSTVFeature("HOLE", "v", 50.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 250.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 450.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 650.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 850.0, 100.0, diameter=22.0),
        ]
    )

    indexer = Indexer(window_width=200.0, overlap=50.0)
    cycles = indexer.plan_beam(beam)

    # Should have multiple windows
    index_cycles = [c for c in cycles if c.type == "INDEX"]
    assert len(index_cycles) >= 3, f"Expected at least 3 INDEX cycles, got {len(index_cycles)}"

    # Verify INDEX cycles advance window position
    if len(index_cycles) > 1:
        assert index_cycles[1].target_position > index_cycles[0].target_position, \
            "Window should advance with each INDEX"


def test_spanning_feature_bisection():
    """Feature longer than window should trigger SEVER."""
    beam = DSTVData(
        filename="span_beam.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=500.0,
        features=[
            # Slot that spans from 50mm to 350mm (300mm long, exceeds 200mm window)
            DSTVFeature("CUT", "v", 50.0, 100.0, path_length=300.0),
        ]
    )

    indexer = Indexer(window_width=200.0, overlap=50.0)
    cycles = indexer.plan_beam(beam)

    # Should have SEVER cycle for spanning feature
    sever_cycles = [c for c in cycles if c.type == "SEVER"]
    assert len(sever_cycles) >= 1, "Expected SEVER cycle for spanning feature"

    # Verify sever length is reasonable (should be profile height)
    assert sever_cycles[0].sever_length > 0, "Sever length must be positive"


def test_empty_beam():
    """Beam with no features should return empty cycle list."""
    beam = DSTVData(
        filename="empty.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=1000.0,
        features=[]
    )

    indexer = Indexer()
    cycles = indexer.plan_beam(beam)

    assert len(cycles) == 0, "Empty beam should produce no cycles"


def test_window_overlap():
    """Verify window overlap is applied correctly."""
    beam = DSTVData(
        filename="test.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=400.0,
        features=[
            DSTVFeature("HOLE", "v", 180.0, 100.0, diameter=22.0),  # Near window boundary
        ]
    )

    indexer = Indexer(window_width=200.0, overlap=50.0)
    cycles = indexer.plan_beam(beam)

    # Feature at 180mm should fit in first window (0-200mm) with overlap
    process_cycles = [c for c in cycles if c.type == "PROCESS"]
    assert len(process_cycles) >= 1, "Should have PROCESS cycle"


def test_multiple_features_different_faces():
    """Features on different faces should all be included in PROCESS cycle."""
    beam = DSTVData(
        filename="multi_face.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=500.0,
        features=[
            DSTVFeature("HOLE", "v", 50.0, 100.0, diameter=22.0),  # Web
            DSTVFeature("HOLE", "o", 50.0, 50.0, diameter=18.0),   # Top flange
            DSTVFeature("HOLE", "u", 50.0, 50.0, diameter=18.0),   # Bottom flange
        ]
    )

    indexer = Indexer(window_width=200.0)
    cycles = indexer.plan_beam(beam)

    process_cycles = [c for c in cycles if c.type == "PROCESS"]
    assert len(process_cycles) >= 1, "Should have PROCESS cycle"

    # All features at same X should be in same cycle
    assert len(process_cycles[0].features) == 3, "Should process all three features"


def test_cycle_sequence():
    """Verify cycles are generated in correct sequence."""
    beam = DSTVData(
        filename="sequence.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=400.0,
        features=[
            DSTVFeature("HOLE", "v", 50.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 250.0, 100.0, diameter=22.0),
        ]
    )

    indexer = Indexer(window_width=200.0, overlap=50.0)
    cycles = indexer.plan_beam(beam)

    # Expected sequence: PROCESS (first feature) -> INDEX -> PROCESS (second feature)
    assert len(cycles) >= 3, f"Expected at least 3 cycles, got {len(cycles)}"

    # First cycle should be PROCESS
    assert cycles[0].type == "PROCESS", "First cycle should be PROCESS"

    # Should have at least one INDEX cycle
    index_cycles = [c for c in cycles if c.type == "INDEX"]
    assert len(index_cycles) >= 1, "Should have INDEX cycle"


def test_feature_at_zero():
    """Feature at X=0 should be processed correctly."""
    beam = DSTVData(
        filename="zero.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=300.0,
        features=[
            DSTVFeature("HOLE", "v", 0.0, 100.0, diameter=22.0),
        ]
    )

    indexer = Indexer(window_width=200.0)
    cycles = indexer.plan_beam(beam)

    process_cycles = [c for c in cycles if c.type == "PROCESS"]
    assert len(process_cycles) >= 1, "Should process feature at X=0"
    assert len(process_cycles[0].features) == 1, "Should include feature at X=0"


def test_backward_compatibility():
    """Legacy group_features method should still work."""
    beam = DSTVData(
        filename="legacy.nc1",
        profile_code="W12x40",
        material_grade="ASTM A36",
        length_mm=500.0,
        features=[
            DSTVFeature("HOLE", "v", 100.0, 100.0, diameter=22.0),
            DSTVFeature("HOLE", "v", 100.5, 150.0, diameter=18.0),
            DSTVFeature("HOLE", "v", 300.0, 100.0, diameter=22.0),
        ]
    )

    indexer = Indexer(tolerance_mm=1.0)
    grouped = indexer.group_features(beam)

    # Should group first two features (within 1mm tolerance)
    assert len(grouped) == 2, "Should have 2 groups"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
