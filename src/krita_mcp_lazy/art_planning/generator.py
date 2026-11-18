"""Visual art production specification generator and composition grid calculator."""

from typing import Any, Dict, List, Optional, Tuple

from krita_mcp_lazy.art_planning.models import (
    CanvasDimensions,
    CompositionRule,
    DepthPlanes,
    LightSource,
    LightingScheme,
    StyleProfile,
    VisualProductionSpec,
)


class ArtPlanner:
    """Calculates cinematic compositions, color harmonies, lighting schemes, and production specs."""

    def calculate_dimensions(self, width: int, aspect_ratio: str, dpi: int = 300) -> CanvasDimensions:
        """Calculate pixel height based on width and aspect ratio string (e.g. '16:9', '4:3', '1:1')."""
        ratio_map = {
            "16:9": (16, 9),
            "1:1": (1, 1),
            "4:3": (4, 3),
            "9:16": (9, 16),
            "21:9": (21, 9),
            "3:2": (3, 2),
        }
        if aspect_ratio in ratio_map:
            num, den = ratio_map[aspect_ratio]
        elif ":" in aspect_ratio:
            parts = aspect_ratio.split(":")
            try:
                num = float(parts[0])
                den = float(parts[1])
            except ValueError:
                num, den = (16, 9)
        else:
            num, den = (16, 9)

        height = int(round(width * (den / num)))
        return CanvasDimensions(width=width, height=height, dpi=dpi)

    def _get_palette_for_style(self, style: StyleProfile) -> List[str]:
        """Generate a curated 5-color harmony palette based on the chosen art style."""
        palettes = {
            StyleProfile.ANIME_CINEMATIC: [
                "#1a1c2e",  # Deep twilight navy (Shadows)
                "#3a506b",  # Steel slate blue (Midtone)
                "#5bc0be",  # Cyan highlight / eye pop
                "#f7f7ff",  # Soft white highlight
                "#ff6b6b",  # Warm sunset accent
            ],
            StyleProfile.STYLIZED_TOON: [
                "#2b2d42",  # Crisp contour black/navy
                "#8d99ae",  # Neutral grey-blue
                "#edf2f4",  # Base clean white
                "#ef233c",  # Vibrant cartoon red
                "#ffb703",  # Punchy cartoon gold
            ],
            StyleProfile.WESTERN_COMIC: [
                "#111111",  # Pure high-contrast inking black
                "#d90429",  # Primary dynamic red
                "#0077b6",  # Comic book cobalt blue
                "#ffd166",  # Pop-art warm yellow
                "#f8f9fa",  # Halftone highlight paper
            ],
            StyleProfile.CONCEPT_ART: [
                "#1e2022",  # Atmospheric dark
                "#52616b",  # Foggy mountain midtone
                "#c9d6df",  # Diffuse ambient sky
                "#f0f5f5",  # Rim light high value
                "#e28743",  # Practical warm lantern / spark
            ],
            StyleProfile.PAINTERLY: [
                "#283618",  # Earthy olive shadow
                "#606c38",  # Foliage midtone
                "#dda15e",  # Warm ochre skin/light
                "#bc6c25",  # Burnt sienna transition
                "#fefae0",  # Natural daylight impasto
            ],
        }
        return palettes.get(style, palettes[StyleProfile.ANIME_CINEMATIC])

    def generate_spec(
        self,
        subject: str,
        aspect_ratio: str = "16:9",
        canvas_width: int = 3840,
        style: StyleProfile = StyleProfile.ANIME_CINEMATIC,
        composition: CompositionRule = CompositionRule.RULE_OF_THIRDS,
        notes: Optional[str] = None,
    ) -> VisualProductionSpec:
        """Synthesize a complete visual production contract for art production."""
        dimensions = self.calculate_dimensions(width=canvas_width, aspect_ratio=aspect_ratio)
        palette = self._get_palette_for_style(style)

        # Depth planes
        depth_plan = DepthPlanes(
            foreground=[f"Foreground silhouettes / framing elements for '{subject}'"],
            midground=[f"Primary subject: {subject}", "Key narrative props and interactions"],
            background=["Environment horizon, architecture, and atmospheric sky/lighting"],
        )

        # Layer blueprint mapped to depth
        layer_blueprint = [
            "00_Background_Atmosphere",
            "01_Environment_Back",
            "02_Midground_Subject_Base",
            "03_Subject_Lineart",
            "04_Subject_Shading_Highlights",
            "05_Foreground_Framing",
            "06_Color_Grading_VFX",
        ]

        # 3-Point Lighting scheme
        lighting = LightingScheme(
            key_light=LightSource(
                role="Key Light",
                direction="Top-Right 45 degrees",
                color_temp_k=5600,
                intensity=1.0,
                color_hex="#fff6e5",
            ),
            fill_light=LightSource(
                role="Fill Light",
                direction="Opposite Left 30 degrees",
                color_temp_k=7200,
                intensity=0.4,
                color_hex="#b8d5e5",
            ),
            rim_light=LightSource(
                role="Rim / Hair Light",
                direction="Behind Subject 135 degrees",
                color_temp_k=6500,
                intensity=0.8,
                color_hex="#e0f0ff",
            ),
            ambient_bounce="Ground ambient diffuse bounce (approx 15% intensity)",
        )

        return VisualProductionSpec(
            subject=subject,
            style=style,
            composition=composition,
            aspect_ratio=aspect_ratio,
            dimensions=dimensions,
            color_palette=palette,
            depth_plan=depth_plan,
            layer_blueprint=layer_blueprint,
            lighting=lighting,
            notes=notes or f"Production spec for {subject} using {style.value} style and {composition.value} grid.",
        )

    def calculate_composition_grid(
        self,
        width: int,
        height: int,
        rule: CompositionRule = CompositionRule.RULE_OF_THIRDS,
    ) -> Dict[str, Any]:
        """Calculate exact pixel coordinates for grid guides and intersection focal points."""
        w = float(width)
        h = float(height)

        if rule == CompositionRule.RULE_OF_THIRDS:
            h_lines = [round(h / 3.0, 1), round(2.0 * h / 3.0, 1)]
            v_lines = [round(w / 3.0, 1), round(2.0 * w / 3.0, 1)]
            focal_points = [
                (v_lines[0], h_lines[0]),
                (v_lines[1], h_lines[0]),
                (v_lines[0], h_lines[1]),
                (v_lines[1], h_lines[1]),
            ]
        elif rule == CompositionRule.GOLDEN_RATIO:
            phi = 0.61803398875
            h_lines = [round(h * (1.0 - phi), 1), round(h * phi, 1)]
            v_lines = [round(w * (1.0 - phi), 1), round(w * phi, 1)]
            focal_points = [
                (v_lines[0], h_lines[0]),
                (v_lines[1], h_lines[0]),
                (v_lines[0], h_lines[1]),
                (v_lines[1], h_lines[1]),
            ]
        elif rule == CompositionRule.CENTER_FOCUS:
            h_lines = [round(h / 2.0, 1)]
            v_lines = [round(w / 2.0, 1)]
            focal_points = [(round(w / 2.0, 1), round(h / 2.0, 1))]
        else:
            # Fallback / Diagonal
            h_lines = [round(h / 2.0, 1)]
            v_lines = [round(w / 2.0, 1)]
            focal_points = [(round(w / 2.0, 1), round(h / 2.0, 1))]

        return {
            "rule": rule.value,
            "canvas_width": width,
            "canvas_height": height,
            "horizontal_lines": h_lines,
            "vertical_lines": v_lines,
            "focal_points": focal_points,
        }
