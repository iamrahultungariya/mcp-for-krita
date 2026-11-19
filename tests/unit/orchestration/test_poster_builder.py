"""Unit tests for AnimePosterBuilder canvas initialization and scaffolding."""

import pytest
from unittest.mock import AsyncMock
from src.krita_mcp_lazy.orchestration.poster_builder import AnimePosterBuilder
from src.krita_mcp_lazy.core.schemas import JobResponse, JobStatus


@pytest.mark.asyncio
async def test_scaffold_poster_document():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="test-job-1",
        status=JobStatus.SUCCESS,
        result={"doc_id": "doc_poster_001", "success": True},
    )

    builder = AnimePosterBuilder(mock_client)
    doc_id = await builder.initialize_canvas()
    assert doc_id == "doc_poster_001"

    # Verify canvas creation call
    create_call = mock_client.send_job.call_args_list[0]
    assert create_call[0][0] == "document.create"
    assert create_call[0][1]["width"] == 2480
    assert create_call[0][1]["height"] == 3508

    # Scaffold groups
    await builder.scaffold_semantic_groups(doc_id)
    assert mock_client.send_job.call_count >= 7


@pytest.mark.asyncio
async def test_paint_celestial_sky_and_city():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="test-job-celestial",
        status=JobStatus.SUCCESS,
        result={"success": True},
    )
    builder = AnimePosterBuilder(mock_client)
    await builder.paint_celestial_environment("doc_test")
    # Must paint sky gradient, stars, moon, and distant skyline
    assert mock_client.send_job.call_count >= 4


@pytest.mark.asyncio
async def test_paint_hero_characters_and_thread():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="test-job-heroes",
        status=JobStatus.SUCCESS,
        result={"success": True},
    )
    builder = AnimePosterBuilder(mock_client)
    await builder.paint_hero_characters_and_thread("doc_test")
    # Must paint balcony railing, girl silhouette, boy silhouette, and red thread
    assert mock_client.send_job.call_count >= 4


