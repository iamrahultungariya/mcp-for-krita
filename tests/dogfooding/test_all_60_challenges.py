import pytest
from krita_mcp_lazy.dogfooding.challenges import get_all_challenges
from krita_mcp_lazy.dogfooding.runner import DogfoodingRunner


def test_challenges_registry():
    challenges = get_all_challenges()
    assert len(challenges) == 60  # Exactly 60 benchmarks across 8 categories

    categories = {c.category for c in challenges}
    assert len(categories) == 8
    assert "character_illustration" in categories
    assert "environment_background" in categories
    assert "props_materials" in categories
    assert "drawing_intelligence" in categories
    assert "advanced_visual" in categories
    assert "document_stress" in categories
    assert "animation_production" in categories
    assert "visual_correction" in categories


@pytest.mark.asyncio
async def test_dogfooding_runner_execution():
    runner = DogfoodingRunner()
    # Run a sample batch of first 5 challenges
    sample_challenges = get_all_challenges()[:5]
    report = await runner.run_challenges(sample_challenges)

    assert report.total_run == 5
    assert report.passed_count == 5
    assert report.failed_count == 0
    assert report.average_score >= 85.0
    assert len(report.results) == 5
    assert report.execution_time_ms > 0.0


@pytest.mark.asyncio
async def test_full_60_dogfooding_suite_execution():
    runner = DogfoodingRunner()
    all_challenges = get_all_challenges()
    report = await runner.run_challenges(all_challenges)

    assert report.total_run == 60
    assert report.passed_count == 60
    assert report.failed_count == 0
    assert report.average_score >= 85.0
    assert report.all_passed is True
