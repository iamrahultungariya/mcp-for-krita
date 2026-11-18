import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.interop_tahoma2d.models import CutoutManifest, CutoutPartMeta
from krita_mcp_lazy.interop_tahoma2d.packager import AssetPackager


@pytest.mark.asyncio
async def test_cutout_asset_packaging():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "manifest": {
            "character": "Hero",
            "parts": [
                {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
                {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4},
            ],
            "canvas_width": 1920,
            "canvas_height": 1080,
        },
        "output_directory": "/tmp/tahoma_pkg",
    }

    packager = AssetPackager(client=mock_client)
    res = await packager.package_character_cutout(
        doc_id="doc_1",
        character_group="grp_hero",
        output_dir="/tmp/tahoma_pkg",
    )
    assert res["manifest"]["character"] == "Hero"
    assert len(res["manifest"]["parts"]) == 2
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "tahoma2d.package_cutout"


@pytest.mark.asyncio
async def test_cutout_packaging_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Character group grp_nonexistent not found",
    }

    packager = AssetPackager(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await packager.package_character_cutout(
            doc_id="doc_1",
            character_group="grp_nonexistent",
            output_dir="/tmp/tahoma_pkg",
        )
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_tahoma2d_package_tool_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_package_tahoma2d_assets" in tool_names
