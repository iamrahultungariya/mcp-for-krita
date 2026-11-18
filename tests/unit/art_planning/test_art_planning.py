import pytest
from pydantic import ValidationError

from krita_mcp_lazy.art_planning.generator import ArtPlanner
from krita_mcp_lazy.art_planning.models import (
    CompositionRule,
    StyleProfile,
    VisualProductionSpec,
)


def test_generate_production_spec():
    planner = ArtPlanner()
    spec = planner.generate_spec(
        subject="Cyberpunk detective in rainy alley",
        aspect_ratio="16:9",
        canvas_width=3840,
        style=StyleProfile.ANIME_CINEMATIC,
        composition=CompositionRule.RULE_OF_THIRDS,
    )
    assert isinstance(spec, VisualProductionSpec)
    assert spec.dimensions.width == 3840
    assert spec.dimensions.height == 2160
    assert len(spec.color_palette) >= 5
    assert spec.depth_plan.foreground is not None
    assert spec.depth_plan.background is not None
    assert len(spec.layer_blueprint) >= 4
    assert spec.lighting.key_light is not None
    assert spec.lighting.fill_light is not None
    assert spec.lighting.rim_light is not None


def test_aspect_ratio_calculations():
    planner = ArtPlanner()

    # 1:1 Square
    spec_square = planner.generate_spec(
        subject="Character portrait",
        aspect_ratio="1:1",
        canvas_width=2048,
    )
    assert spec_square.dimensions.height == 2048

    # 4:3
    spec_43 = planner.generate_spec(
        subject="Classic landscape",
        aspect_ratio="4:3",
        canvas_width=2400,
    )
    assert spec_43.dimensions.height == 1800

    # 9:16 Portrait
    spec_916 = planner.generate_spec(
        subject="Mobile wallpaper",
        aspect_ratio="9:16",
        canvas_width=1080,
    )
    assert spec_916.dimensions.height == 1920


def test_calculate_composition_grid():
    planner = ArtPlanner()
    grid_thirds = planner.calculate_composition_grid(
        width=3000,
        height=1500,
        rule=CompositionRule.RULE_OF_THIRDS,
    )
    assert grid_thirds["rule"] == "RULE_OF_THIRDS"
    assert len(grid_thirds["horizontal_lines"]) == 2
    assert len(grid_thirds["vertical_lines"]) == 2
    assert len(grid_thirds["focal_points"]) == 4
    # (1000, 500), (2000, 500), (1000, 1000), (2000, 1000)
    assert (1000.0, 500.0) in [(p[0], p[1]) for p in grid_thirds["focal_points"]]

    grid_golden = planner.calculate_composition_grid(
        width=1000,
        height=1000,
        rule=CompositionRule.GOLDEN_RATIO,
    )
    assert grid_golden["rule"] == "GOLDEN_RATIO"
    assert len(grid_golden["focal_points"]) == 4


def test_mcp_art_planning_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_generate_production_spec" in tool_names
    assert "krita_calculate_composition_grid" in tool_names
