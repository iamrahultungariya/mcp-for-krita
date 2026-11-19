"""Anime movie poster builder orchestrating Krita IPC actions into a high-production anime poster."""

import logging
from typing import Any, Dict, List, Optional
from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec

logger = logging.getLogger(__name__)


class AnimePosterBuilder:
    """Orchestrates procedural anime poster composition and rendering via Krita IPC client."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self.spec = get_whispers_in_starlight_spec()

    async def initialize_canvas(self) -> str:
        """Create new A4 300 DPI canvas for the anime movie poster."""
        canvas_cfg = self.spec["canvas"]
        res = await self.client.send_job(
            "document.create",
            {
                "width": canvas_cfg["width"],
                "height": canvas_cfg["height"],
                "name": canvas_cfg["name"],
                "resolution_dpi": canvas_cfg["dpi"],
                "color_model": canvas_cfg["color_model"],
                "color_depth": canvas_cfg["color_depth"],
            },
        )
        doc_id = res.result.get("doc_id", "doc_poster_001")
        logger.info("Initialized anime poster canvas with doc_id: %s", doc_id)
        return doc_id

    async def scaffold_semantic_groups(self, doc_id: str) -> Dict[str, Any]:
        """Scaffold non-destructive layer hierarchy and parent semantic groups."""
        created_layers: Dict[str, str] = {}
        layers_spec = self.spec["layers"]

        for group_name, group_cfg in layers_spec.items():
            # 1. Create Parent Group Layer
            res_grp = await self.client.send_job(
                "layer.create",
                {
                    "doc_id": doc_id,
                    "name": group_name,
                    "layer_type": "groupLayer",
                    "opacity": group_cfg.get("opacity", 255),
                    "blending_mode": group_cfg.get("blend_mode", "normal"),
                },
            )
            created_layers[group_name] = res_grp.result.get("layer_id", group_name)

            # 2. Create child paint layers
            for child_name in group_cfg.get("children", []):
                blend = "addition" if any(w in child_name.lower() for w in ["glow", "lights", "bokeh", "orbs"]) else "normal"
                res_child = await self.client.send_job(
                    "layer.create",
                    {
                        "doc_id": doc_id,
                        "name": child_name,
                        "layer_type": "paintLayer",
                        "parent_id": group_name,
                        "blending_mode": blend,
                    },
                )
                created_layers[child_name] = res_child.result.get("layer_id", child_name)

        return created_layers

    async def paint_celestial_environment(self, doc_id: str) -> None:
        """Paint rich twilight sky gradient, crescent moon, stars, and distant cityline."""
        palette = self.spec["palette"]

        # 1. Sky Gradient Layers (horizontal sweeps from top to horizon)
        gradient_bands = [
            (palette["sky_zenith"], 200, 450.0),
            (palette["sky_zenith"], 700, 450.0),
            (palette["sky_mid"], 1300, 450.0),
            (palette["sky_mid"], 1800, 450.0),
            (palette["sky_twilight"], 2250, 350.0),
            (palette["horizon_glow"], 2600, 250.0),
        ]
        for color, y_pos, size in gradient_bands:
            await self.client.send_job(
                "stroke.paint",
                {
                    "doc_id": doc_id,
                    "layer_id": "Sky_Gradient",
                    "points": [
                        {"x": 0, "y": y_pos, "pressure": 1.0},
                        {"x": 1240, "y": y_pos, "pressure": 1.0},
                        {"x": 2480, "y": y_pos, "pressure": 1.0},
                    ],
                    "color": color,
                    "size": size,
                    "opacity": 0.95,
                },
            )

        # 2. Glowing Crescent Moon
        moon_x, moon_y = self.spec["composition"]["moon_center"]
        # Outer soft aura
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Crescent_Moon",
                "points": [{"x": moon_x, "y": moon_y, "pressure": 1.0}],
                "color": palette["starlight_glow"],
                "size": 280.0,
                "opacity": 0.4,
            },
        )
        # Moon crescent body
        moon_arc = [
            {"x": moon_x - 70, "y": moon_y - 80, "pressure": 0.4},
            {"x": moon_x, "y": moon_y - 100, "pressure": 0.8},
            {"x": moon_x + 70, "y": moon_y - 40, "pressure": 1.0},
            {"x": moon_x + 90, "y": moon_y + 40, "pressure": 1.0},
            {"x": moon_x + 50, "y": moon_y + 90, "pressure": 0.8},
            {"x": moon_x - 30, "y": moon_y + 110, "pressure": 0.4},
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Crescent_Moon",
                "points": moon_arc,
                "color": palette["starlight_core"],
                "size": 35.0,
                "opacity": 1.0,
            },
        )

        # 3. Celestial Starlight Field & Constellations
        import random
        random.seed(42)  # Deterministic starlight pattern
        star_points: List[dict] = []
        for _ in range(75):
            sx = random.randint(50, 2430)
            sy = random.randint(50, 2100)
            sp = random.uniform(0.3, 0.9)
            star_points.append({"x": sx, "y": sy, "pressure": sp})

        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Stars_Field",
                "points": star_points,
                "color": palette["starlight_core"],
                "size": 10.0,
                "opacity": 0.9,
            },
        )

        # 4. Distant City Skyline Silhouettes
        city_points = [
            {"x": 0, "y": 2680, "pressure": 1.0},
            {"x": 400, "y": 2640, "pressure": 1.0},
            {"x": 700, "y": 2610, "pressure": 1.0},
            {"x": 1000, "y": 2650, "pressure": 1.0},
            {"x": 1300, "y": 2600, "pressure": 1.0},
            {"x": 1600, "y": 2620, "pressure": 1.0},
            {"x": 2000, "y": 2590, "pressure": 1.0},
            {"x": 2480, "y": 2650, "pressure": 1.0},
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "City_Skyline",
                "points": city_points,
                "color": palette["city_silhouette"],
                "size": 120.0,
                "opacity": 1.0,
            },
        )

        # 5. Twinkling Warm City Lights (windows along skyline)
        window_lights: List[dict] = []
        for wx in range(100, 2400, 60):
            wy = random.randint(2620, 2720)
            window_lights.append({"x": wx, "y": wy, "pressure": random.uniform(0.4, 0.9)})

        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "City_Window_Lights",
                "points": window_lights,
                "color": palette["city_lights"],
                "size": 6.0,
                "opacity": 0.95,
            },
        )

    async def paint_hero_characters_and_thread(self, doc_id: str) -> None:
        """Paint observation deck railing, lovers silhouettes, and the glowing red thread of destiny."""
        palette = self.spec["palette"]

        # 1. Observation Balcony Floor & Railing
        # Floor base
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Balcony_Floor",
                "points": [
                    {"x": 0, "y": 3200, "pressure": 1.0},
                    {"x": 1240, "y": 3200, "pressure": 1.0},
                    {"x": 2480, "y": 3200, "pressure": 1.0},
                ],
                "color": palette["architecture_deck"],
                "size": 400.0,
                "opacity": 1.0,
            },
        )
        # Top Railing bar
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Observation_Railing",
                "points": [
                    {"x": 0, "y": 2880, "pressure": 1.0},
                    {"x": 2480, "y": 2880, "pressure": 1.0},
                ],
                "color": palette["architecture_deck"],
                "size": 25.0,
                "opacity": 1.0,
            },
        )

        # 2. Hero Girl Silhouette (Anime heroine reaching rightward)
        girl_body_strokes = [
            {"x": 750, "y": 3100, "pressure": 1.0},  # Lower skirt
            {"x": 770, "y": 2950, "pressure": 0.9},  # Waist
            {"x": 780, "y": 2820, "pressure": 0.8},  # Torso
            {"x": 785, "y": 2720, "pressure": 0.7},  # Neck & head base
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Girl_Silhouette",
                "points": girl_body_strokes,
                "color": palette["character_silhouette"],
                "size": 90.0,
                "opacity": 1.0,
            },
        )
        # Girl head & flowing twin-tail hair
        girl_hair = [
            {"x": 785, "y": 2680, "pressure": 0.9},
            {"x": 750, "y": 2720, "pressure": 0.8},
            {"x": 680, "y": 2780, "pressure": 0.7},
            {"x": 620, "y": 2850, "pressure": 0.4},  # Hair blowing in wind
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Girl_Silhouette",
                "points": girl_hair,
                "color": palette["character_silhouette"],
                "size": 55.0,
                "opacity": 1.0,
            },
        )
        # Girl reaching arm & hand towards center
        girl_arm = [
            {"x": 810, "y": 2800, "pressure": 0.8},
            {"x": 930, "y": 2770, "pressure": 0.6},
            {"x": 1050, "y": 2740, "pressure": 0.5},
            {"x": 1150, "y": 2720, "pressure": 0.3},  # Fingertip
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Girl_Silhouette",
                "points": girl_arm,
                "color": palette["character_silhouette"],
                "size": 22.0,
                "opacity": 1.0,
            },
        )

        # 3. Hero Boy Silhouette (Anime boy leaning forward, reaching leftward)
        boy_body_strokes = [
            {"x": 1720, "y": 3100, "pressure": 1.0},
            {"x": 1700, "y": 2940, "pressure": 0.9},
            {"x": 1680, "y": 2800, "pressure": 0.85},
            {"x": 1660, "y": 2690, "pressure": 0.75},  # Neck & head
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Boy_Silhouette",
                "points": boy_body_strokes,
                "color": palette["character_silhouette"],
                "size": 105.0,
                "opacity": 1.0,
            },
        )
        # Boy hair profile
        boy_hair = [
            {"x": 1660, "y": 2650, "pressure": 0.9},
            {"x": 1630, "y": 2680, "pressure": 0.7},
            {"x": 1675, "y": 2630, "pressure": 0.6},
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Boy_Silhouette",
                "points": boy_hair,
                "color": palette["character_silhouette"],
                "size": 60.0,
                "opacity": 1.0,
            },
        )
        # Boy reaching arm towards center
        boy_arm = [
            {"x": 1640, "y": 2780, "pressure": 0.8},
            {"x": 1520, "y": 2760, "pressure": 0.6},
            {"x": 1420, "y": 2740, "pressure": 0.5},
            {"x": 1330, "y": 2720, "pressure": 0.3},  # Fingertip
        ]
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Hero_Boy_Silhouette",
                "points": boy_arm,
                "color": palette["character_silhouette"],
                "size": 26.0,
                "opacity": 1.0,
            },
        )

        # 4. Red Thread of Fate (flowing curve linking their fingertips)
        thread_points = [
            {"x": 1150, "y": 2720, "pressure": 0.4},
            {"x": 1180, "y": 2760, "pressure": 0.8},
            {"x": 1240, "y": 2810, "pressure": 1.0},  # Lower drape
            {"x": 1300, "y": 2760, "pressure": 0.8},
            {"x": 1330, "y": 2720, "pressure": 0.4},
        ]
        # Core glowing crimson thread
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Red_Thread_Fate",
                "points": thread_points,
                "color": palette["fate_thread"],
                "size": 8.0,
                "opacity": 1.0,
            },
        )
        # Soft outer glowing aura
        await self.client.send_job(
            "stroke.paint",
            {
                "doc_id": doc_id,
                "layer_id": "Thread_Glow",
                "points": thread_points,
                "color": palette["fate_glow"],
                "size": 32.0,
                "opacity": 0.65,
            },
        )

    async def paint_atmosphere_and_petals(self, doc_id: str) -> None:
        """Stub for Task 7 atmosphere painting."""
        pass

    async def render_cinematic_typography(self, doc_id: str) -> None:
        """Stub for Task 7 typography rendering."""
        pass
