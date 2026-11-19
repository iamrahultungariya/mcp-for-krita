"""Painting Director orchestrating multi-layer anime poster composition with soft brush simulation."""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from krita_mcp_lazy.brush_sim.soft_brush import (
    build_airbrush_region,
    paint_airbrush_pass,
    paint_glow_halo,
    paint_ink_stroke,
    paint_soft_stroke,
)
from krita_mcp_lazy.painting_director.layers import LayerBuffer


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex string (#RGB or #RRGGBB) to (r, g, b) tuple."""
    hex_clean = hex_code.lstrip("#")
    if len(hex_clean) == 3:
        return (
            int(hex_clean[0] * 2, 16),
            int(hex_clean[1] * 2, 16),
            int(hex_clean[2] * 2, 16),
        )
    elif len(hex_clean) >= 6:
        return (
            int(hex_clean[0:2], 16),
            int(hex_clean[2:4], 16),
            int(hex_clean[4:6], 16),
        )
    return (255, 255, 255)


class PaintingDirector:
    """Directs layer-by-layer digital painting synthesis using authentic brush physics."""

    def __init__(self, spec: Dict[str, Any]) -> None:
        self.spec = spec
        self.palette = spec.get("palette", {})
        self.title_info = spec.get("title", {})

    def render_all_layers(
        self,
        width: int,
        height: int,
        gemini_art: Optional[Image.Image] = None,
    ) -> List[LayerBuffer]:
        """Synthesize all semantic poster layers into isolated LayerBuffer instances."""
        layers: List[LayerBuffer] = [
            self._render_sky_gradient(width, height),
            self._render_nebula_glow(width, height),
            self._render_stars_field(width, height),
            self._render_crescent_moon(width, height),
            self._render_distant_city(width, height),
            self._render_observation_deck(width, height),
            self._render_hero_characters(width, height, gemini_art),
            self._render_rim_lighting(width, height),
            self._render_red_thread(width, height),
            self._render_sakura_petals(width, height),
            self._render_typography(width, height),
        ]
        return layers

    def _render_sky_gradient(self, w: int, h: int) -> LayerBuffer:
        """Sky gradient rendered as seamless atmospheric airbrush sweeps."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        c_zenith = hex_to_rgb(self.palette.get("sky_zenith", "#0B1026"))
        c_mid = hex_to_rgb(self.palette.get("sky_mid", "#261B4E"))
        c_twilight = hex_to_rgb(self.palette.get("sky_twilight", "#E86A82"))
        c_horizon = hex_to_rgb(self.palette.get("horizon_glow", "#FCD0A1"))

        color_stops = [
            (0.0, c_zenith),
            (0.40, c_mid),
            (0.75, c_twilight),
            (1.0, c_horizon),
        ]

        # Interpolate vertical lines for butter-smooth gradient
        for y in range(h):
            pos = y / max(1, h - 1)
            # Find the segment
            for i in range(len(color_stops) - 1):
                p0, col0 = color_stops[i]
                p1, col1 = color_stops[i + 1]
                if p0 <= pos <= p1:
                    factor = (pos - p0) / max(1e-5, (p1 - p0))
                    r = int(col0[0] + factor * (col1[0] - col0[0]))
                    g = int(col0[1] + factor * (col1[1] - col0[1]))
                    b = int(col0[2] + factor * (col1[2] - col0[2]))
                    draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
                    break

        return LayerBuffer("00_Sky_Gradient", canvas.tobytes(), 0, 0, w, h)

    def _render_nebula_glow(self, w: int, h: int) -> LayerBuffer:
        """Ethereal cosmic nebula dust painted with soft airbrush clusters."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        c_cyan = hex_to_rgb(self.palette.get("celestial_cyan", "#64DFDF"))
        c_mid = hex_to_rgb(self.palette.get("sky_mid", "#261B4E"))

        centers = [
            (int(w * 0.25), int(h * 0.35)),
            (int(w * 0.50), int(h * 0.25)),
            (int(w * 0.70), int(h * 0.40)),
            (int(w * 0.85), int(h * 0.20)),
        ]
        radius = max(20, int(w * 0.22))
        for idx, pt in enumerate(centers):
            color = c_cyan if idx % 2 == 0 else c_mid
            canvas = build_airbrush_region(canvas, pt, radius, color, passes=3)

        return LayerBuffer("01_Nebula_Glow", canvas.tobytes(), 0, 0, w, h, blend_mode="screen")

    def _render_stars_field(self, w: int, h: int) -> LayerBuffer:
        """Star constellation field with multi-point bloom and twinkle radiance."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        rng = random.Random(42)

        star_count = max(40, int(w * h / 18000))
        sky_limit_y = int(h * 0.72)
        bright_stars = []

        for _ in range(star_count):
            sx = rng.randint(0, w - 1)
            sy = rng.randint(0, sky_limit_y)
            brightness = rng.randint(190, 255)
            r = 1 if rng.random() > 0.15 else 2
            alpha = rng.randint(180, 255)

            draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(brightness, brightness, 255, alpha))
            if r > 1 and rng.random() > 0.4:
                bright_stars.append((sx, sy))

        # Add bloom halos to prominent stars
        c_star_glow = hex_to_rgb(self.palette.get("starlight_glow", "#FFF3B0"))
        for bx, by in bright_stars[:15]:
            canvas = paint_glow_halo(canvas, (bx, by), radius=max(4, int(w * 0.012)), color=c_star_glow)

        return LayerBuffer("02_Stars_Field", canvas.tobytes(), 0, 0, w, h, blend_mode="screen")

    def _render_crescent_moon(self, w: int, h: int) -> LayerBuffer:
        """Stylized anime crescent moon with soft luminous outer glow."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        cx = int(w * 0.76)
        cy = int(h * 0.18)
        r = max(10, int(w * 0.075))

        # Soft glow pass first
        c_moon_glow = hex_to_rgb(self.palette.get("starlight_glow", "#FFF3B0"))
        canvas = paint_glow_halo(canvas, (cx, cy), radius=int(r * 2.2), color=c_moon_glow)

        # Moon disc
        moon_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_m = ImageDraw.Draw(moon_layer)
        draw_m.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 245, 255))

        # Crescent shadow cutout using midnight sky color
        c_sky = hex_to_rgb(self.palette.get("sky_zenith", "#0B1026"))
        offset_x = int(r * 0.38)
        draw_m.ellipse(
            [cx - r + offset_x, cy - r - int(r * 0.1), cx + r + offset_x, cy + r + int(r * 0.1)],
            fill=(*c_sky, 255),
        )

        moon_layer = moon_layer.filter(ImageFilter.GaussianBlur(radius=max(1.0, r * 0.08)))
        canvas.alpha_composite(moon_layer)

        return LayerBuffer("03_Crescent_Moon", canvas.tobytes(), 0, 0, w, h)

    def _render_distant_city(self, w: int, h: int) -> LayerBuffer:
        """Distant skyline and mountains with warm twinkling window points."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        c_city = hex_to_rgb(self.palette.get("city_silhouette", "#080C1B"))
        c_light = hex_to_rgb(self.palette.get("city_lights", "#FFD166"))

        horizon_y = int(h * 0.72)

        # Mountain silhouette behind
        rng = random.Random(101)
        mountain_points = [(0, h), (0, horizon_y)]
        step = max(10, w // 20)
        for x in range(0, w + step, step):
            my = horizon_y - rng.randint(int(h * 0.02), int(h * 0.07))
            mountain_points.append((x, my))
        mountain_points.append((w, h))
        draw.polygon(mountain_points, fill=(*c_city, 255))

        # City buildings cluster
        b_x = int(w * 0.15)
        while b_x < int(w * 0.85):
            bw = rng.randint(int(w * 0.03), int(w * 0.08))
            bh = rng.randint(int(h * 0.05), int(h * 0.12))
            by = horizon_y - bh + int(h * 0.03)
            draw.rectangle([b_x, by, b_x + bw, h], fill=(*c_city, 255))

            # Warm window lights
            for wy in range(by + 5, horizon_y, max(4, int(h * 0.015))):
                for wx in range(b_x + 4, b_x + bw - 4, max(4, int(w * 0.015))):
                    if rng.random() > 0.45:
                        draw.rectangle([wx, wy, wx + 2, wy + 2], fill=(*c_light, 240))
            b_x += bw + rng.randint(2, 8)

        return LayerBuffer("04_City_Skyline", canvas.tobytes(), 0, 0, w, h)

    def _render_observation_deck(self, w: int, h: int) -> LayerBuffer:
        """Rooftop observation deck floor and safety railing."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        c_deck = hex_to_rgb(self.palette.get("architecture_deck", "#10142A"))

        deck_y = int(h * 0.80)
        draw.rectangle([0, deck_y, w, h], fill=(*c_deck, 255))

        # Horizontal railing bars
        r_color = (*c_deck, 255)
        bar_y1 = int(h * 0.75)
        bar_y2 = int(h * 0.775)
        draw.line([(0, bar_y1), (w, bar_y1)], fill=r_color, width=max(2, int(h * 0.005)))
        draw.line([(0, bar_y2), (w, bar_y2)], fill=r_color, width=max(2, int(h * 0.004)))

        # Vertical balusters
        spacing = max(15, int(w * 0.06))
        for vx in range(0, w, spacing):
            draw.line([(vx, bar_y1), (vx, deck_y)], fill=r_color, width=max(2, int(w * 0.003)))

        return LayerBuffer("05_Rooftop_Observation", canvas.tobytes(), 0, 0, w, h)

    def _render_hero_characters(
        self,
        w: int,
        h: int,
        gemini_art: Optional[Image.Image] = None,
    ) -> LayerBuffer:
        """Hero anime characters (boy & girl gazing at the stars) or Gemini art."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        if gemini_art is not None:
            # Composite Gemini key art if provided
            fitted = gemini_art.resize((w, h), Image.LANCZOS).convert("RGBA")
            canvas.alpha_composite(fitted)
            return LayerBuffer("06_Hero_Characters", canvas.tobytes(), 0, 0, w, h)

        # Procedural silhouette anime figures
        c_char = hex_to_rgb(self.palette.get("character_silhouette", "#0D1127"))
        draw = ImageDraw.Draw(canvas)

        base_y = int(h * 0.80)

        # Girl silhouette (left)
        gx = int(w * 0.35)
        gh = int(h * 0.17)
        # Head
        gr = max(8, int(w * 0.038))
        draw.ellipse([gx - gr, base_y - gh - gr * 2, gx + gr, base_y - gh], fill=(*c_char, 255))
        # Hair stream blowing leftwards
        hair_pts = [
            (gx, base_y - gh - gr),
            (gx - int(gr * 2.2), base_y - gh - gr // 2),
            (gx - int(gr * 1.5), base_y - gh + gr),
            (gx, base_y - gh + gr // 2),
        ]
        draw.polygon(hair_pts, fill=(*c_char, 255))
        # Torso / dress
        torso_pts = [
            (gx - gr, base_y - gh),
            (gx + gr, base_y - gh),
            (gx + int(gr * 1.8), base_y),
            (gx - int(gr * 1.8), base_y),
        ]
        draw.polygon(torso_pts, fill=(*c_char, 255))

        # Boy silhouette (right)
        bx = int(w * 0.65)
        bh = int(h * 0.19)
        br = max(9, int(w * 0.042))
        # Head
        draw.ellipse([bx - br, base_y - bh - br * 2, bx + br, base_y - bh], fill=(*c_char, 255))
        # Torso / jacket
        boy_pts = [
            (bx - br, base_y - bh),
            (bx + br, base_y - bh),
            (bx + int(br * 1.5), base_y),
            (bx - int(br * 1.5), base_y),
        ]
        draw.polygon(boy_pts, fill=(*c_char, 255))

        return LayerBuffer("06_Hero_Characters", canvas.tobytes(), 0, 0, w, h)

    def _render_rim_lighting(self, w: int, h: int) -> LayerBuffer:
        """Gentle twilight rim light tracing character silhouettes."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        c_rim = hex_to_rgb(self.palette.get("sky_twilight", "#E86A82"))

        base_y = int(h * 0.80)
        gx = int(w * 0.35)
        gh = int(h * 0.17)
        gr = max(8, int(w * 0.038))

        # Stroke highlighting girl's back
        rim_pts = [
            {"x": gx + gr - 1, "y": base_y - gh - gr * 2 + 3},
            {"x": gx + gr + 1, "y": base_y - gh},
            {"x": gx + int(gr * 1.8) - 1, "y": base_y - int(gh * 0.3)},
        ]
        canvas = paint_ink_stroke(canvas, rim_pts, color=c_rim, width=max(2, int(w * 0.005)))

        return LayerBuffer("07_Rim_Lighting", canvas.tobytes(), 0, 0, w, h, blend_mode="screen")

    def _render_red_thread(self, w: int, h: int) -> LayerBuffer:
        """The red thread of fate linking lovers' hands."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        c_thread = hex_to_rgb(self.palette.get("fate_thread", "#FF2A55"))
        c_bloom = hex_to_rgb(self.palette.get("fate_glow", "#FFAAA6"))

        p0 = (int(w * 0.38), int(h * 0.74))
        p1 = (int(w * 0.50), int(h * 0.77))
        p2 = (int(w * 0.62), int(h * 0.74))

        # Sample Bézier curve points
        pts: List[dict] = []
        steps = 30
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            pts.append({"x": int(x), "y": int(y)})

        # Ink stroke
        canvas = paint_ink_stroke(canvas, pts, color=c_thread, width=max(2, int(w * 0.005)))
        # Soft bloom around the heart knot center
        canvas = paint_glow_halo(canvas, (p1[0], p1[1]), radius=max(8, int(w * 0.02)), color=c_bloom)

        return LayerBuffer("08_Red_Thread_Fate", canvas.tobytes(), 0, 0, w, h)

    def _render_sakura_petals(self, w: int, h: int) -> LayerBuffer:
        """Drifting cherry blossom petals with varied orientation and depth scale."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        c_sakura = hex_to_rgb(self.palette.get("sakura_base", "#FFB7B2"))
        rng = random.Random(77)

        petal_count = max(25, int(w * h / 30000))
        for _ in range(petal_count):
            px = rng.randint(0, w - 1)
            py = rng.randint(int(h * 0.15), int(h * 0.90))

            # Petal stamp
            pr = rng.randint(max(3, int(w * 0.005)), max(6, int(w * 0.014)))
            petal = Image.new("RGBA", (pr * 4, pr * 4), (0, 0, 0, 0))
            draw_p = ImageDraw.Draw(petal)
            draw_p.ellipse([pr, pr // 2, pr * 3, pr * 3], fill=(*c_sakura, rng.randint(180, 240)))

            # Rotate randomly
            angle = rng.randint(0, 360)
            petal = petal.rotate(angle, resample=Image.BICUBIC)

            canvas.alpha_composite(petal, dest=(px - pr * 2, py - pr * 2))

        return LayerBuffer("09_Sakura_Petals", canvas.tobytes(), 0, 0, w, h)

    def _render_typography(self, w: int, h: int) -> LayerBuffer:
        """Movie typography with cinematic title, Japanese kanji, and billing credit."""
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        c_kanji = hex_to_rgb(self.palette.get("title_kanji", "#FFFFFF"))
        c_sub = hex_to_rgb(self.palette.get("title_sub", "#FCD0A1"))

        # Font resolution
        font_size_title = max(14, int(w * 0.055))
        font_size_sub = max(10, int(w * 0.026))

        font_title = self._load_font(font_size_title)
        font_sub = self._load_font(font_size_sub)

        # Title: 『星空の約束』 / "WHISPERS IN THE STARLIGHT"
        en_title = self.title_info.get("english", "WHISPERS IN THE STARLIGHT").upper()
        jp_title = self.title_info.get("japanese", "星空の約束")
        tagline = self.title_info.get("tagline", "Across infinite skies, our hearts remember.")
        release = self.title_info.get("release", "COMING TO THEATERS SUMMER 2026")

        ty = int(h * 0.86)
        draw.text((w // 2, ty), en_title, fill=(*c_kanji, 255), font=font_title, anchor="mm")
        draw.text((w // 2, ty + int(font_size_title * 0.8)), tagline, fill=(*c_sub, 230), font=font_sub, anchor="mm")
        draw.text((w // 2, int(h * 0.95)), release, fill=(*c_kanji, 200), font=font_sub, anchor="mm")

        return LayerBuffer("10_Movie_Typography", canvas.tobytes(), 0, 0, w, h)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Safe font loader looking for Windows default system fonts with fallback."""
        candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\msgothic.ttc",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
        return ImageFont.load_default()


def composite_to_png(layers: List[LayerBuffer], width: int, height: int, output_path: str) -> None:
    """Flatten all layer buffers into a single presentation-grade PNG."""
    final_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    for layer in layers:
        layer_img = Image.frombytes("RGBA", (layer.width, layer.height), layer.pixels)

        if layer.blend_mode == "screen":
            base_rgb = final_canvas.convert("RGB")
            layer_rgb = layer_img.convert("RGB")
            screened = ImageChops.screen(base_rgb, layer_rgb).convert("RGBA")
            # Preserve alpha composite mask
            screened.putalpha(layer_img.getchannel("A"))
            final_canvas.alpha_composite(screened)
        else:
            final_canvas.alpha_composite(layer_img)

    final_canvas.save(output_path, "PNG")
