"""Tests for autonomous painter MCP tool."""

import os
from unittest.mock import AsyncMock, patch
from PIL import Image
import pytest


@pytest.mark.asyncio
async def test_paint_poster_paints_all_layers(tmp_path):
    """paint_poster should orchestrate director rendering, stream tiles, and save flat composite."""
    from krita_mcp_lazy.server.tools_autonomous_painter import paint_poster

    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "layer_id": "lyr_mock_1",
        "created": True,
        "success": True,
    }

    out_png = str(tmp_path / "test_autonomous_poster.png")
    result = await paint_poster(
        prompt="Whispers in the Starlight anime poster",
        doc_id="doc_auto_001",
        width=200,
        height=300,
        client=mock_client,
        output_png_path=out_png,
    )

    assert result["layers_painted"] >= 10
    assert len(result["layer_names"]) >= 10
    assert os.path.exists(out_png)

    # Verify PNG has content
    img = Image.open(out_png)
    assert img.size == (200, 300)


@pytest.mark.asyncio
async def test_paint_poster_with_user_image(tmp_path):
    """paint_poster should accept user_image_path and integrate it into composition."""
    from krita_mcp_lazy.server.tools_autonomous_painter import paint_poster

    user_img = Image.new("RGBA", (100, 150), (200, 50, 100, 255))
    user_img_path = str(tmp_path / "custom_art.png")
    user_img.save(user_img_path)

    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "layer_id": "lyr_user",
        "created": True,
        "success": True,
    }

    out_png = str(tmp_path / "poster_with_user_art.png")
    result = await paint_poster(
        prompt="Anime love poster",
        doc_id="doc_auto_002",
        width=200,
        height=300,
        client=mock_client,
        user_image_path=user_img_path,
        output_png_path=out_png,
    )

    assert result["layers_painted"] >= 10
    assert os.path.exists(out_png)
