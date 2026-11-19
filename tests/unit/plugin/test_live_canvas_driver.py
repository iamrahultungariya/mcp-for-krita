"""Unit tests for Real Progressive Live Canvas Driver."""

import pytest
from plugins.krita_mcp_bridge.canvas_tablet_driver import (
    CanvasTabletDriver,
    hex_to_bgra,
)


def test_hex_to_bgra_channel_order():
    """Verify that hex color converts strictly to Krita native BGRA byte order."""
    # #1A365D -> R=0x1A, G=0x36, B=0x5D, A=255
    bgra = hex_to_bgra("#1A365D", opacity=1.0)
    assert bgra == (0x5D, 0x36, 0x1A, 255)

    # Pure Red: #FF0000 -> B=0, G=0, R=255, A=255
    red_bgra = hex_to_bgra("#FF0000", opacity=1.0)
    assert red_bgra == (0, 0, 255, 255)

    # Pure Blue: #0000FF -> B=255, G=0, R=0, A=255
    blue_bgra = hex_to_bgra("#0000FF", opacity=1.0)
    assert blue_bgra == (255, 0, 0, 255)


def test_execute_live_stroke_renders_and_returns_bounding_box():
    driver = CanvasTabletDriver()
    points = [
        {"x": 100.0, "y": 100.0, "pressure": 0.2},
        {"x": 150.0, "y": 120.0, "pressure": 0.8},
        {"x": 200.0, "y": 140.0, "pressure": 0.3},
    ]
    result = driver.execute_live_stroke(
        points=points,
        preset_name="f)_Ink-3_Gpen",
        color_hex="#1A365D",
        size=8.0,
        doc_id="doc_mock",
        layer_name="06_Lineart",
    )
    assert result["success"] is True
    assert result["points_drawn"] == 3
    assert "bounding_box" in result
    bbox = result["bounding_box"]
    assert bbox[0] < 100 and bbox[2] > 200
    assert "pixel_data_updated" in result
    assert result["pixel_data_updated"] is True
