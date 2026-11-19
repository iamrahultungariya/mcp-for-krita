"""Unit tests for in-app Krita color grading and adjustment layer generator."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from krita_mcp_lazy.color_grading.adjustments import ColorGradingManager, GradingProfile


def test_generate_golden_hour_grading_spec():
    manager = ColorGradingManager()
    spec = manager.get_profile_spec("golden_hour_anime")
    assert spec.warm_highlight_tint == "#FFF3B0"
    assert spec.deep_shadow_tint == "#1E152A"
    assert len(spec.layers) >= 2


def test_generate_dusk_cinematic_grading_spec():
    manager = ColorGradingManager()
    spec = manager.get_profile_spec("dusk_cinematic")
    assert spec.warm_highlight_tint == "#FF9E00"
    assert spec.deep_shadow_tint == "#240046"
    assert len(spec.layers) >= 2


@pytest.mark.asyncio
async def test_scaffold_color_grading_stack_dispatches_ipc():
    manager = ColorGradingManager()
    mock_client = AsyncMock()
    mock_client.send_job.return_value = MagicMock(result={"success": True})

    res = await manager.scaffold_color_grading_stack(
        client=mock_client,
        doc_id="doc_test",
        profile="golden_hour_anime",
    )
    assert res["success"] is True
    assert res["profile"] == "golden_hour_anime"
    assert res["layers_created"] >= 2
    assert mock_client.send_job.call_count >= 2
