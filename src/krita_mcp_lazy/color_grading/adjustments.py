"""Native Krita in-app color grading and adjustment layer generator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GradingLayerSpec:
    """Specification for an in-app adjustment or color grading layer."""
    name: str
    layer_type: str = "adjustmentLayer"   # "adjustmentLayer" or "paintLayer"
    blending_mode: str = "normal"         # "screen", "multiply", "soft_light", "overlay"
    opacity: int = 255                    # 0..255
    filter_name: Optional[str] = None     # e.g. "cross_channel", "colorbalance", "curves"
    filter_params: Optional[Dict[str, Any]] = None
    fill_color_hex: Optional[str] = None  # For atmospheric tint layers


@dataclass
class GradingProfile:
    """Preset color grading profile with atmospheric tints and adjustment layers."""
    name: str
    description: str
    warm_highlight_tint: str
    deep_shadow_tint: str
    layers: List[GradingLayerSpec] = field(default_factory=list)


class ColorGradingManager:
    """Manages creation and configuration of native Krita color grading stacks."""

    def __init__(self) -> None:
        self.profiles: Dict[str, GradingProfile] = {
            "golden_hour_anime": GradingProfile(
                name="golden_hour_anime",
                description="High-contrast warm golden sunlight with cool violet cel shadows and bloom",
                warm_highlight_tint="#FFF3B0",
                deep_shadow_tint="#1E152A",
                layers=[
                    GradingLayerSpec(
                        name="Grade_Warm_Sun_Bloom",
                        layer_type="paintLayer",
                        blending_mode="screen",
                        opacity=160,
                        fill_color_hex="#FFF3B0",
                    ),
                    GradingLayerSpec(
                        name="Grade_Cool_Cel_Ambient",
                        layer_type="paintLayer",
                        blending_mode="multiply",
                        opacity=190,
                        fill_color_hex="#1E152A",
                    ),
                    GradingLayerSpec(
                        name="Grade_Cinematic_Contrast",
                        layer_type="adjustmentLayer",
                        blending_mode="soft_light",
                        opacity=140,
                        filter_name="curves",
                    ),
                ],
            ),
            "dusk_cinematic": GradingProfile(
                name="dusk_cinematic",
                description="Deep indigo twilight with saturated amber/orange rim lighting",
                warm_highlight_tint="#FF9E00",
                deep_shadow_tint="#240046",
                layers=[
                    GradingLayerSpec(
                        name="Grade_Dusk_Glow",
                        layer_type="paintLayer",
                        blending_mode="screen",
                        opacity=175,
                        fill_color_hex="#FF9E00",
                    ),
                    GradingLayerSpec(
                        name="Grade_Twilight_Shadows",
                        layer_type="paintLayer",
                        blending_mode="multiply",
                        opacity=210,
                        fill_color_hex="#240046",
                    ),
                    GradingLayerSpec(
                        name="Grade_Contrast_Curves",
                        layer_type="adjustmentLayer",
                        blending_mode="overlay",
                        opacity=120,
                        filter_name="curves",
                    ),
                ],
            ),
            "studio_neutral": GradingProfile(
                name="studio_neutral",
                description="Clean, balanced anime TV broadcast grade with pure whites",
                warm_highlight_tint="#FFFFFF",
                deep_shadow_tint="#1A1A24",
                layers=[
                    GradingLayerSpec(
                        name="Grade_Studio_Softlight",
                        layer_type="adjustmentLayer",
                        blending_mode="soft_light",
                        opacity=100,
                        filter_name="colorbalance",
                    ),
                    GradingLayerSpec(
                        name="Grade_Neutral_Curves",
                        layer_type="adjustmentLayer",
                        blending_mode="normal",
                        opacity=150,
                        filter_name="curves",
                    ),
                ],
            ),
        }

    def get_profile_spec(self, profile_name: str) -> GradingProfile:
        """Retrieve grading profile specification by name, falling back to golden_hour_anime."""
        return self.profiles.get(profile_name, self.profiles["golden_hour_anime"])

    async def scaffold_color_grading_stack(
        self,
        client: Any,
        doc_id: str,
        profile: str = "golden_hour_anime",
    ) -> Dict[str, Any]:
        """Inject complete color grading layer stack into target Krita document."""
        spec = self.get_profile_spec(profile)
        created_layers: List[str] = []

        # 1. Create Color Grading Group Layer
        group_name = f"FX_Color_Grade_{spec.name}"
        await client.send_job(
            "layer.create",
            {
                "doc_id": doc_id,
                "name": group_name,
                "layer_type": "groupLayer",
                "blending_mode": "normal",
                "opacity": 255,
            },
        )
        created_layers.append(group_name)

        # 2. Inject constituent adjustment and tint layers into group
        for lyr in spec.layers:
            job_params: Dict[str, Any] = {
                "doc_id": doc_id,
                "name": lyr.name,
                "layer_type": lyr.layer_type,
                "blending_mode": lyr.blending_mode,
                "opacity": lyr.opacity,
                "parent_group": group_name,
            }
            if lyr.filter_name:
                job_params["filter_name"] = lyr.filter_name
            if lyr.filter_params:
                job_params["filter_params"] = lyr.filter_params
            if lyr.fill_color_hex:
                job_params["fill_color"] = lyr.fill_color_hex

            res = await client.send_job("layer.create", job_params)
            created_layers.append(lyr.name)

        # 3. Refresh canvas
        await client.send_job("document.refresh", {"doc_id": doc_id})

        return {
            "success": True,
            "doc_id": doc_id,
            "profile": spec.name,
            "group_name": group_name,
            "layers_created": len(created_layers),
            "layer_names": created_layers,
        }
