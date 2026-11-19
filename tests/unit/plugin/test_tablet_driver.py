"""Tests for CanvasCoordinateTransformer and CanvasTabletDriver."""

import pytest
from plugins.krita_mcp_bridge.canvas_tablet_driver import (
    CanvasCoordinateTransformer,
    CanvasTabletDriver,
)


def test_coordinate_transformer_affine_mapping():
    """Verify linear coordinate transformation between document and canvas widget."""
    transformer = CanvasCoordinateTransformer()
    transformer.calibrate_from_points(
        doc_pts=[(0.0, 0.0), (1000.0, 1000.0)],
        view_pts=[(100.0, 50.0), (1100.0, 1050.0)],
    )

    assert transformer.calibrated is True

    # Test midpoint
    vx, vy = transformer.doc_to_view(500.0, 500.0)
    assert abs(vx - 600.0) < 1e-3
    assert abs(vy - 550.0) < 1e-3

    # Test quarter point
    vx2, vy2 = transformer.doc_to_view(250.0, 250.0)
    assert abs(vx2 - 350.0) < 1e-3
    assert abs(vy2 - 300.0) < 1e-3


def test_coordinate_transformer_default_identity():
    """Uncalibrated transformer should behave as 1:1 identity mapping."""
    transformer = CanvasCoordinateTransformer()
    assert transformer.calibrated is False
    vx, vy = transformer.doc_to_view(120.0, 240.0)
    assert vx == 120.0
    assert vy == 240.0


def test_tablet_driver_headless_simulation():
    """Verify tablet driver can simulate and validate stroke points with pressure."""
    driver = CanvasTabletDriver()
    transformer = CanvasCoordinateTransformer()

    points = [
        {"x": 10.0, "y": 20.0, "pressure": 0.2},
        {"x": 50.0, "y": 60.0, "pressure": 0.8},
        {"x": 90.0, "y": 100.0, "pressure": 0.15},
    ]

    report = driver.simulate_stroke_sequence(
        points=points,
        preset_name="f)_Ink-3_Gpen",
        transformer=transformer,
    )

    assert report["success"] is True
    assert report["preset"] == "f)_Ink-3_Gpen"
    assert report["point_count"] == 3
    assert report["tapered"] is True
    assert report["max_pressure"] == 0.8
    assert report["min_pressure"] == 0.15
