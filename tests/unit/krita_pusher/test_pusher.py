"""Tests for KritaPusher tile streaming and live canvas refreshing."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from krita_mcp_lazy.krita_pusher.pusher import KritaPusher
from krita_mcp_lazy.painting_director.layers import LayerBuffer


@pytest.mark.asyncio
async def test_pusher_creates_layer_and_streams_tiles():
    """KritaPusher must create layer, stream tiles in chunks, and refresh document."""
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "layer_id": "lyr_sky_01",
        "name": "00_Sky_Gradient",
        "created": True,
        "success": True,
    }

    pusher = KritaPusher(mock_client, tile_height=100)
    # 200 width, 250 height -> requires 3 tiles (100, 100, 50)
    w, h = 200, 250
    pixels = bytes([255, 0, 0, 255] * (w * h))
    buf = LayerBuffer("00_Sky_Gradient", pixels, 0, 0, w, h, blend_mode="normal", opacity=255)

    result = await pusher.push_layer("doc_test", buf)

    assert result["name"] == "00_Sky_Gradient"
    assert result["layer_id"] == "lyr_sky_01"

    # Inspect call actions
    calls = [c[0][0] for c in mock_client.send_job.call_args_list]
    assert calls[0] == "layer.create"
    # Should have 3 tile calls
    tile_calls = [c for c in calls if c == "layer.set_pixel_tile"]
    assert len(tile_calls) == 3
    # Final call should refresh
    assert calls[-1] == "document.refresh"


@pytest.mark.asyncio
async def test_pusher_uses_screen_blend_mode():
    """Layers marked screen blend must pass that blend mode to layer.create."""
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"layer_id": "lyr_glow"}

    pusher = KritaPusher(mock_client, tile_height=50)
    w, h = 100, 50
    pixels = bytes([0] * (w * h * 4))
    buf = LayerBuffer("01_Nebula_Glow", pixels, 0, 0, w, h, blend_mode="screen", opacity=200)

    await pusher.push_layer("doc_test", buf)
    create_call = mock_client.send_job.call_args_list[0]
    assert create_call[0][0] == "layer.create"
    params = create_call[0][1]
    assert params["blending_mode"] == "screen"
    assert params["opacity"] == 200
