"""
Professional soft brush simulator.

Every brush primitive is a Gaussian-feathered blob — never a flat PIL ellipse.
This is what separates professional digital painting from scribble output.

Core insight:
  flat_ellipse → hard aliased disc  (MS Paint level)
  ellipse + GaussianBlur → feathered brush stamp  (professional level)
  stacked blobs (screen blend) → glow / bloom  (cinematic level)
"""

from __future__ import annotations

import math
from typing import List, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

# ---------------------------------------------------------------------------
# Internal primitive: a single brush stamp
# ---------------------------------------------------------------------------

def _make_soft_stamp(radius: int, color: Tuple[int, int, int], opacity: float) -> Image.Image:
    """
    One feathered round brush stamp.

    Strategy:
      1. Draw a solid disc on a 4× oversize RGBA canvas.
      2. GaussianBlur with sigma = radius * 0.45  → smooth edge falloff.
      3. Opacity baked into alpha.

    Returns an RGBA image ready to alpha_composite onto any canvas.
    """
    size = max(8, radius * 4)
    stamp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)

    cx = size // 2
    alpha = max(1, min(255, int(255 * opacity)))
    r, g, b = color[0], color[1], color[2]

    # Solid disc — will be blurred into a feathered edge
    draw.ellipse(
        [cx - radius, cx - radius, cx + radius, cx + radius],
        fill=(r, g, b, alpha),
    )

    # Gaussian blur = the feathered edge (this IS the brush softness)
    sigma = max(1.0, radius * 0.45)
    return stamp.filter(ImageFilter.GaussianBlur(radius=sigma))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def paint_soft_stroke(
    canvas: Image.Image,
    points: List[dict],
    color: Tuple[int, int, int],
    radius: int,
    opacity: float = 1.0,
) -> Image.Image:
    """
    Paint a pressure-sensitive soft round brush stroke along a list of points.

    Each point dict: {"x": int, "y": int, "pressure": float 0-1}
    Pressure scales the stamp size — lighter pressure = smaller mark.

    Uses alpha_composite so overlapping strokes build up correctly.
    """
    result = canvas.copy()
    base_stamp = _make_soft_stamp(radius, color, opacity)
    base_size = base_stamp.size[0]

    for pt in points:
        x = int(pt["x"])
        y = int(pt["y"])
        pressure = float(pt.get("pressure", 1.0))
        pressure = max(0.1, min(1.0, pressure))

        # Scale stamp by pressure
        scaled_size = max(4, int(base_size * pressure))
        if scaled_size != base_size:
            stamp = base_stamp.resize((scaled_size, scaled_size), Image.LANCZOS)
        else:
            stamp = base_stamp

        half = stamp.size[0] // 2
        paste_x = x - half
        paste_y = y - half

        # Clamp to canvas bounds
        if paste_x >= result.width or paste_y >= result.height:
            continue
        if paste_x + stamp.size[0] <= 0 or paste_y + stamp.size[1] <= 0:
            continue

        result.alpha_composite(stamp, dest=(paste_x, paste_y))

    return result


def paint_airbrush_pass(
    canvas: Image.Image,
    center: Tuple[int, int],
    radius: int,
    color: Tuple[int, int, int],
    opacity: float = 0.12,
) -> Image.Image:
    """
    One airbrush pass: very large soft blob, very low opacity.

    Key difference from soft brush:
      - Radius is 2-4× larger (airbrush sprays wide)
      - Opacity is very low (0.08-0.15 per pass)
      - Blur sigma is 60% of radius (extra soft)
    """
    size = max(8, radius * 4)
    blob = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(blob)

    cx = size // 2
    alpha = max(1, min(255, int(255 * opacity)))
    draw.ellipse(
        [cx - radius, cx - radius, cx + radius, cx + radius],
        fill=(*color[:3], alpha),
    )

    # Extra soft sigma for airbrush
    sigma = max(1.0, radius * 0.60)
    blob = blob.filter(ImageFilter.GaussianBlur(radius=sigma))

    result = canvas.copy()
    cx_paste = center[0] - size // 2
    cy_paste = center[1] - size // 2

    if cx_paste < result.width and cy_paste < result.height:
        result.alpha_composite(blob, dest=(cx_paste, cy_paste))

    return result


def build_airbrush_region(
    canvas: Image.Image,
    center: Tuple[int, int],
    radius: int,
    color: Tuple[int, int, int],
    passes: int = 6,
) -> Image.Image:
    """
    Stack multiple low-opacity airbrush passes.

    This is how digital painters build up smooth color areas:
    each pass adds a little — after 6 passes the area is richly colored
    but with natural, gradual falloff from center to edge.

    Per-pass opacity deliberately kept low (0.12) so buildup is gradual.
    """
    result = canvas.copy()
    per_pass_opacity = 0.12
    for _ in range(passes):
        result = paint_airbrush_pass(result, center, radius, color, per_pass_opacity)
    return result


def paint_glow_halo(
    canvas: Image.Image,
    center: Tuple[int, int],
    radius: int,
    color: Tuple[int, int, int],
) -> Image.Image:
    """
    Screen-blend glow halo — the professional bloom technique.

    Algorithm:
      1. Draw a soft blob at center on a transparent layer.
      2. GaussianBlur it heavily → this blurred blob IS the glow.
      3. Screen-blend onto canvas → always brightens, never darkens.

    Screen formula: result = 1 - (1-A)(1-B)
    This matches Krita/Photoshop 'Screen' blend mode exactly.
    """
    w, h = canvas.size

    # Glow blob on transparent layer
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    cx, cy = center
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(*color[:3], 180),
    )

    # Heavy blur = spread of glow beyond the source shape
    sigma = max(2.0, radius * 0.8)
    glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=sigma))

    # Screen blend (must work on RGB — convert, screen, restore alpha)
    base_rgb = canvas.convert("RGB")
    glow_rgb = glow_blurred.convert("RGB")
    screened_rgb = ImageChops.screen(base_rgb, glow_rgb)

    result = screened_rgb.convert("RGBA")
    # Preserve original canvas alpha (don't blow out transparent areas)
    result.putalpha(canvas.getchannel("A"))
    return result


def paint_ink_stroke(
    canvas: Image.Image,
    points: List[dict],
    color: Tuple[int, int, int],
    width: int = 3,
) -> Image.Image:
    """
    Ink brush stroke: hard edge with slight Gaussian feather.

    Looks like a real ink liner — decisive, full-opacity line
    with just enough blur to remove pixel aliasing.
    """
    # Draw on a fresh transparent layer then composite
    ink_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ink_layer)

    for i in range(1, len(points)):
        p0 = points[i - 1]
        p1 = points[i]
        draw.line(
            [(int(p0["x"]), int(p0["y"])), (int(p1["x"]), int(p1["y"]))],
            fill=(*color[:3], 255),
            width=width,
        )
        # Round caps: draw circles at each point
        for pt in (p0, p1):
            r = width // 2
            px, py = int(pt["x"]), int(pt["y"])
            draw.ellipse([px - r, py - r, px + r, py + r], fill=(*color[:3], 255))

    # Very slight feather — removes aliasing, keeps ink feel
    ink_layer = ink_layer.filter(ImageFilter.GaussianBlur(radius=0.7))

    result = canvas.copy()
    result.alpha_composite(ink_layer)
    return result
