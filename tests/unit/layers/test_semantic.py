import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.layers.semantic import (
    ARCHETYPE_PRESETS,
    SemanticLayerOrganizer,
)
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_scaffold_character_hierarchy():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_scaffold_1",
        status=JobStatus.SUCCESS,
        result={"created_groups": 3, "created_layers": 7, "doc_id": "doc_1"},
    )

    organizer = SemanticLayerOrganizer(client=mock_client)
    schema = {
        "Character": {
            "Head": ["Hair", "Face", "Eyes", "Mouth"],
            "Body": ["Clothing", "Limbs", "Torso"],
        }
    }
    res = await organizer.scaffold_hierarchy(doc_id="doc_1", schema=schema)
    assert res["created_layers"] == 7
    assert res["created_groups"] == 3

    sent_req = mock_client.send_job.call_args[0][0]
    assert sent_req.action == "layer.scaffold_semantic"
    assert sent_req.params["schema"] == schema


@pytest.mark.asyncio
async def test_scaffold_preset_archetype():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_scaffold_preset",
        status=JobStatus.SUCCESS,
        result={"created_groups": 5, "created_layers": 12, "preset": "character_production"},
    )

    organizer = SemanticLayerOrganizer(client=mock_client)
    res = await organizer.scaffold_hierarchy(doc_id="doc_1", preset="character_production")
    assert res["preset"] == "character_production"
    assert res["created_groups"] == 5

    assert "character_production" in ARCHETYPE_PRESETS
    assert "environment_depth" in ARCHETYPE_PRESETS
    assert "prop_asset" in ARCHETYPE_PRESETS


@pytest.mark.asyncio
async def test_semantic_error_handling():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_err",
        status=JobStatus.FAILED,
        error="Invalid hierarchy schema: empty dictionary",
        error_code=ErrorCode.LAYER_ERROR.value,
    )

    organizer = SemanticLayerOrganizer(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await organizer.scaffold_hierarchy(doc_id="doc_1", schema={})
    assert exc_info.value.code == ErrorCode.LAYER_ERROR
    assert "Invalid hierarchy" in exc_info.value.message


@pytest.mark.asyncio
async def test_mcp_scaffold_tool_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]

    assert "krita_scaffold_semantic_structure" in tool_names
