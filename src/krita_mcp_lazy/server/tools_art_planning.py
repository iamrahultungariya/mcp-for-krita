"""MCP tools for visual production specifications, composition grids, and art direction."""

from typing import Any, Optional

from krita_mcp_lazy.art_planning.generator import ArtPlanner
from krita_mcp_lazy.art_planning.models import CompositionRule, StyleProfile
from krita_mcp_lazy.core.config import KritaConfig

_planner: Optional[ArtPlanner] = None


def get_art_planner() -> ArtPlanner:
    """Retrieve singleton ArtPlanner instance."""
    global _planner
    if _planner is None:
        _planner = ArtPlanner()
    return _planner


def register_art_planning_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all art direction and composition planning tools on the MCP server."""

    @server.tool(
        name="krita_generate_production_spec",
        description="Generate a comprehensive visual production spec with aspect ratios, color palettes, depth planes, and 3-point lighting",
    )
    async def _tool_generate_production_spec(
        subject: str,
        aspect_ratio: str = "16:9",
        canvas_width: int = 3840,
        style: str = "ANIME_CINEMATIC",
        composition: str = "RULE_OF_THIRDS",
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        planner = get_art_planner()
        try:
            style_enum = StyleProfile(style)
        except ValueError:
            style_enum = StyleProfile.ANIME_CINEMATIC

        try:
            comp_enum = CompositionRule(composition)
        except ValueError:
            comp_enum = CompositionRule.RULE_OF_THIRDS

        spec = planner.generate_spec(
            subject=subject,
            aspect_ratio=aspect_ratio,
            canvas_width=canvas_width,
            style=style_enum,
            composition=comp_enum,
            notes=notes,
        )
        return spec.model_dump()

    @server.tool(
        name="krita_calculate_composition_grid",
        description="Calculate exact pixel lines and focal intersection points for Rule of Thirds, Golden Ratio, or Center Focus",
    )
    async def _tool_calculate_composition_grid(
        width: int,
        height: int,
        rule: str = "RULE_OF_THIRDS",
    ) -> dict[str, Any]:
        planner = get_art_planner()
        try:
            comp_enum = CompositionRule(rule)
        except ValueError:
            comp_enum = CompositionRule.RULE_OF_THIRDS

        return planner.calculate_composition_grid(width=width, height=height, rule=comp_enum)
