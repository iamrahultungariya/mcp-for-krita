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


def test_checkpoint_real_rollback_handler():
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    from plugins.krita_mcp_bridge.handlers_strokes import register_stroke_handlers, _mock_painted_strokes
    from plugins.krita_mcp_bridge.handlers_visual_qa import register_visual_qa_handlers
    from krita_mcp_lazy.core.schemas import JobRequest, JobStatus

    dispatcher = KritaMainThreadDispatcher(max_queue_size=20)
    register_stroke_handlers(dispatcher)
    register_visual_qa_handlers(dispatcher)

    doc_id = "doc_chk_test"
    _mock_painted_strokes[doc_id] = []

    # Draw 1st stroke
    req_s1 = JobRequest(
        action="stroke.paint",
        params={"doc_id": doc_id, "layer_id": "L1", "points": [{"x": 10, "y": 10, "pressure": 0.5}]},
    )
    dispatcher.enqueue(req_s1)
    dispatcher.process_pending_jobs()
    assert len(_mock_painted_strokes[doc_id]) == 1

    # Create checkpoint
    req_cp = JobRequest(action="checkpoint.create", params={"doc_id": doc_id, "label": "cp1"})
    dispatcher.enqueue(req_cp)
    dispatcher.process_pending_jobs()
    chk_id = dispatcher.get_result(req_cp.job_id).result["checkpoint_id"]

    # Draw 2nd stroke
    req_s2 = JobRequest(
        action="stroke.paint",
        params={"doc_id": doc_id, "layer_id": "L1", "points": [{"x": 50, "y": 50, "pressure": 0.8}]},
    )
    dispatcher.enqueue(req_s2)
    dispatcher.process_pending_jobs()
    assert len(_mock_painted_strokes[doc_id]) == 2

    # Rollback to checkpoint
    req_rb = JobRequest(action="checkpoint.rollback", params={"doc_id": doc_id, "checkpoint_id": chk_id})
    dispatcher.enqueue(req_rb)
    dispatcher.process_pending_jobs()
    rb_res = dispatcher.get_result(req_rb.job_id).result
    assert rb_res["restored"] is True
    assert rb_res["checkpoint_id"] == chk_id
    # Assert stroke count rolled back to 1!
    assert len(_mock_painted_strokes[doc_id]) == 1

    # Rollback to non-existent checkpoint returns restored=False
    req_bad_rb = JobRequest(action="checkpoint.rollback", params={"doc_id": doc_id, "checkpoint_id": "chk_nonexistent"})
    dispatcher.enqueue(req_bad_rb)
    dispatcher.process_pending_jobs()
    assert dispatcher.get_result(req_bad_rb.job_id).result["restored"] is False


def test_dynamic_telemetry_and_consistency_handlers():
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    from plugins.krita_mcp_bridge.handlers_animation import register_animation_handlers
    from plugins.krita_mcp_bridge.handlers_character import register_character_handlers
    from krita_mcp_lazy.core.schemas import JobRequest

    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    register_animation_handlers(dispatcher)
    register_character_handlers(dispatcher)

    # 1. Animation keyframe dynamic memory calculation
    req_f0 = JobRequest(action="animation.create_keyframe", params={"frame_index": 0})
    req_f5 = JobRequest(action="animation.create_keyframe", params={"frame_index": 5})
    dispatcher.enqueue(req_f0)
    dispatcher.enqueue(req_f5)
    dispatcher.process_pending_jobs()

    mem_0 = dispatcher.get_result(req_f0.job_id).result["cache_usage_mb"]
    mem_5 = dispatcher.get_result(req_f5.job_id).result["cache_usage_mb"]
    assert mem_0 > 0.0
    assert mem_5 > mem_0  # Memory increases with frame index!
    assert mem_0 != 45.2  # Removed hardcoded 45.2!

    # 2. Character consistency dynamic scoring
    req_c1 = JobRequest(
        action="character.verify_consistency",
        params={"views": ["front", "three_quarter", "side", "back"], "guide_lines": {"eye_line": 500.0, "total_height": 1800.0}},
    )
    req_c2 = JobRequest(
        action="character.verify_consistency",
        params={"views": ["front"], "guide_lines": {}},
    )
    dispatcher.enqueue(req_c1)
    dispatcher.enqueue(req_c2)
    dispatcher.process_pending_jobs()

    score_c1 = dispatcher.get_result(req_c1.job_id).result["consistency_score"]
    score_c2 = dispatcher.get_result(req_c2.job_id).result["consistency_score"]
    assert score_c1 > score_c2  # Full turnaround with guides scores higher!
    assert score_c1 != 92.5 or score_c2 != 92.5  # Dynamic scoring verified!


def test_mcp_scorecard_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_evaluate_visual_quality" in tool_names
    assert "krita_create_checkpoint" in tool_names
    assert "krita_rollback_checkpoint" in tool_names
