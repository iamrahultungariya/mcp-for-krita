import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.character.expressions import (
    EmotionType,
    FacialExpressionEngine,
    VisemeType,
)
from krita_mcp_lazy.core.errors import ErrorCode, KritaError


@pytest.mark.asyncio
async def test_expression_sheet_generation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "character_name": "Kael",
        "emotions": ["neutral", "happy", "angry", "sad", "shocked", "scared"],
        "layers_created": 24,
    }

    engine = FacialExpressionEngine(client=mock_client)
    res = await engine.create_expression_matrix(
        doc_id="doc_1",
        character_name="Kael",
        emotions=[
            EmotionType.NEUTRAL,
            EmotionType.HAPPY,
            EmotionType.ANGRY,
            EmotionType.SAD,
            EmotionType.SHOCKED,
            EmotionType.SCARED,
        ],
    )
    assert len(res["emotions"]) == 6
    assert res["layers_created"] == 24
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "character.expression_matrix"


@pytest.mark.asyncio
async def test_generate_viseme_set():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "character_name": "Kael",
        "visemes": ["rest", "ai", "e", "o", "u", "mbp", "fv", "lntd"],
        "viseme_group": "Kael_Visemes",
    }

    engine = FacialExpressionEngine(client=mock_client)
    res = await engine.generate_viseme_set(doc_id="doc_1", character_name="Kael")
    assert len(res["visemes"]) == 8
    assert res["viseme_group"] == "Kael_Visemes"
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "character.generate_visemes"


@pytest.mark.asyncio
async def test_expression_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Failed to create expression layers",
    }

    engine = FacialExpressionEngine(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await engine.create_expression_matrix(doc_id="invalid_doc")
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_expression_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_create_expression_sheet" in tool_names
    assert "krita_generate_viseme_set" in tool_names
