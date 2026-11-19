"""Unit tests for Cel Studio tools: live anime character painting, modular rig export, and fidelity gate."""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from unittest.mock import AsyncMock, patch

from krita_mcp_lazy.server.tools_cel_studio import (
    export_reusable_rig,
    import_reusable_rig,
    live_paint_anime_character,
    verify_canvas_fidelity,
)


@pytest.mark.asyncio
async def test_live_paint_anime_character_orchestration(tmp_path):
    # Test cartoon input
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.circle(img, (50, 50), 30, (0, 0, 0), 2)
    p = str(tmp_path / "test_char.png")
    cv2.imwrite(p, img)

    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "created": True,
        "layer_id": "lyr_1",
        "inherit_alpha": True,
        "image_base64": "",
        "updated": True,
    }

    out_png = str(tmp_path / "output_test.png")
    res = await live_paint_anime_character(
        image_path=p,
        doc_id="doc_cel_01",
        client=mock_client,
        use_live_tablet=False,
        output_png_path=out_png,
        library_root=str(tmp_path / "library"),
    )

    assert res["success"] is True
    assert res["vector_strokes_count"] >= 1
    assert res["flats_count"] >= 1
    assert "fidelity" in res
    assert res["fidelity"]["ssim"] > 0.0
    assert "manifest_path" in res


@pytest.mark.asyncio
async def test_export_and_import_rig_tools(tmp_path):
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "created": True,
        "layer_id": "lyr_rig",
    }

    lib_dir = str(tmp_path / "rigs")
    res_exp = await export_reusable_rig(
        char_id="creator_bot",
        name="Creator Bot",
        doc_id="doc_01",
        client=mock_client,
        library_root=lib_dir,
    )
    assert res_exp["success"] is True
    assert res_exp["manifest_path"].endswith("rig_manifest.json")

    res_imp = await import_reusable_rig(
        char_id="creator_bot",
        doc_id="doc_02",
        x=100,
        y=200,
        scale=1.5,
        client=mock_client,
        library_root=lib_dir,
    )
    assert res_imp["success"] is True
    assert res_imp["placement"]["x"] == 100


def test_verify_canvas_fidelity_tool(tmp_path):
    # Two identical patches
    ref = np.full((100, 100, 3), 200, dtype=np.uint8)
    cv2.circle(ref, (50, 50), 20, (0, 0, 0), -1)
    p_ref = str(tmp_path / "ref.png")
    cv2.imwrite(p_ref, ref)

    p_rnd = str(tmp_path / "rnd.png")
    cv2.imwrite(p_rnd, ref)

    res = verify_canvas_fidelity(p_ref, p_rnd, min_ssim=0.88, min_edge_iou=0.80)
    assert res["is_approved"] is True
    assert res["ssim"] >= 0.88
