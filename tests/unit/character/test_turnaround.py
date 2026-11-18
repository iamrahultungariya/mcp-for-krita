import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.character.models import CharacterSheetSpec, ViewAngle
from krita_mcp_lazy.character.turnaround import CharacterTurnaroundEngine
from krita_mcp_lazy.core.errors import ErrorCode, KritaError


@pytest.mark.asyncio
async def test_turnaround_sheet_generation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "character_name": "Kael",
        "views_created": ["front", "three_quarter", "side", "back"],
        "guide_lines": {
            "top_of_head": 100.0,
            "eye_line": 150.0,
            "chin_line": 233.3,
            "shoulder_line": 300.0,
            "waist_line": 500.0,
            "ground_line": 1100.0,
        },
    }

    engine = CharacterTurnaroundEngine(client=mock_client)
    spec = CharacterSheetSpec(
        character_name="Kael",
        head_height_ratio=7.5,
        views=[ViewAngle.FRONT, ViewAngle.THREE_QUARTER, ViewAngle.SIDE, ViewAngle.BACK],
    )
    res = await engine.setup_turnaround_canvases(doc_id="doc_1", spec=spec)
    assert len(res["views_created"]) == 4
    assert "guide_lines" in res
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "character.setup_turnaround"


@pytest.mark.asyncio
async def test_verify_character_consistency():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "character_name": "Kael",
        "consistency_score": 92.5,
        "aligned": True,
        "views_checked": ["front", "side"],
        "landmarks": {"eye_line_aligned": True, "height_aligned": True},
    }

    engine = CharacterTurnaroundEngine(client=mock_client)
    res = await engine.verify_character_consistency(
        doc_id="doc_1",
        character_name="Kael",
        views=[ViewAngle.FRONT, ViewAngle.SIDE],
    )
    assert res["consistency_score"] >= 85.0
    assert res["aligned"] is True


@pytest.mark.asyncio
async def test_turnaround_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Document doc_invalid not found",
    }

    engine = CharacterTurnaroundEngine(client=mock_client)
    spec = CharacterSheetSpec(character_name="TestChar")
    with pytest.raises(KritaError) as exc_info:
        await engine.setup_turnaround_canvases(doc_id="doc_invalid", spec=spec)
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_character_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_create_character_turnaround" in tool_names
    assert "krita_verify_character_consistency" in tool_names
