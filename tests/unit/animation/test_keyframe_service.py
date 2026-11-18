import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.animation.keyframe_service import KeyframeService
from krita_mcp_lazy.animation.models import KeyframeType, OnionSkinConfig
from krita_mcp_lazy.core.errors import ErrorCode, KritaError


@pytest.mark.asyncio
async def test_keyframe_creation_with_memory_guard():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "frame_index": 24,
        "cache_usage_mb": 45.2,
        "status": "ok",
        "doc_id": "doc_1",
    }

    svc = KeyframeService(client=mock_client, max_cache_mb=500.0)
    res = await svc.create_keyframe(
        doc_id="doc_1",
        layer_id="lyr_anim",
        frame_index=24,
        keyframe_type=KeyframeType.BLANK,
    )
    assert res["frame_index"] == 24
    assert res["cache_usage_mb"] < 500.0
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "animation.create_keyframe"


@pytest.mark.asyncio
async def test_configure_onion_skin():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "enabled": True,
        "tint_previous": "#ff0000",
        "tint_future": "#00ff00",
        "prev_frames": 3,
        "next_frames": 2,
    }

    svc = KeyframeService(client=mock_client)
    cfg = OnionSkinConfig(
        tint_previous="#ff0000",
        tint_future="#00ff00",
        prev_frames=3,
        next_frames=2,
        opacity=0.6,
    )
    res = await svc.configure_onion_skin(doc_id="doc_1", layer_id="lyr_anim", config=cfg)
    assert res["enabled"] is True
    assert res["prev_frames"] == 3
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "animation.configure_onion_skin"


@pytest.mark.asyncio
async def test_set_frame_timing():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "fps": 24,
        "total_frames": 48,
        "start_time": 0,
        "end_time": 47,
    }

    svc = KeyframeService(client=mock_client)
    res = await svc.set_frame_timing(doc_id="doc_1", fps=24, total_frames=48)
    assert res["fps"] == 24
    assert res["total_frames"] == 48


@pytest.mark.asyncio
async def test_keyframe_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Animation cache limit exceeded",
    }

    svc = KeyframeService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await svc.create_keyframe(doc_id="doc_1", layer_id="lyr_anim", frame_index=1000)
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_animation_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_create_keyframe" in tool_names
    assert "krita_configure_onion_skin" in tool_names
    assert "krita_set_frame_timing" in tool_names
