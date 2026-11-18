import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.visual_qa.rollback import CheckpointManager
from krita_mcp_lazy.visual_qa.scorecard import QualityCriteria, ScorecardEvaluator


def test_scorecard_calculation():
    evaluator = ScorecardEvaluator()
    criteria = QualityCriteria(
        anatomy_proportions=90.0,
        line_quality=85.0,
        composition_perspective=88.0,
        lighting_shading=82.0,
        color_materials=85.0,
        reference_fidelity=90.0,
        detail_finish=80.0,
        layer_editability=95.0,
    )
    score = evaluator.calculate_total(criteria)
    # Weights: 15, 15, 15, 15, 10, 15, 10, 5 = 100%
    # 90*0.15 + 85*0.15 + 88*0.15 + 82*0.15 + 85*0.1 + 90*0.15 + 80*0.1 + 95*0.05
    # = 13.5 + 12.75 + 13.2 + 12.3 + 8.5 + 13.5 + 8.0 + 4.75 = 86.5
    assert score == 86.5
    assert score >= 85.0
    assert evaluator.passes_production_gate(score) is True


def test_scorecard_failure_and_recommendations():
    evaluator = ScorecardEvaluator()
    criteria = QualityCriteria(
        anatomy_proportions=60.0,
        line_quality=65.0,
        composition_perspective=70.0,
        lighting_shading=60.0,
        color_materials=65.0,
        reference_fidelity=70.0,
        detail_finish=60.0,
        layer_editability=80.0,
    )
    evaluation = evaluator.evaluate(criteria)
    assert evaluation["total_score"] < 85.0
    assert evaluation["passed"] is False
    assert len(evaluation["recommendations"]) > 0


@pytest.mark.asyncio
async def test_checkpoint_lifecycle():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "checkpoint_id": "chk_101",
        "doc_id": "doc_1",
        "label": "before_inking",
    }

    mgr = CheckpointManager(client=mock_client)
    cp = await mgr.create_checkpoint(doc_id="doc_1", label="before_inking")
    assert cp["checkpoint_id"] == "chk_101"

    # Rollback
    mock_client.send_job.return_value.result = {
        "restored": True,
        "checkpoint_id": "chk_101",
        "doc_id": "doc_1",
    }
    rb = await mgr.rollback_checkpoint(doc_id="doc_1", checkpoint_id="chk_101")
    assert rb["restored"] is True


def test_mcp_scorecard_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_evaluate_visual_quality" in tool_names
    assert "krita_create_checkpoint" in tool_names
    assert "krita_rollback_checkpoint" in tool_names
