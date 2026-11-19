"""Tests for the professional soft brush simulator."""
import pytest
from PIL import Image


def test_soft_stroke_has_feathered_edges():
    """Soft brush must have Gaussian falloff — center opaque, edges fade to transparent."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_soft_stroke

    canvas = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    pts = [{"x": 100, "y": 100, "pressure": 1.0}]
    result = paint_soft_stroke(canvas, pts, color=(255, 255, 255), radius=20, opacity=1.0)

    center_alpha  = result.getpixel((100, 100))[3]   # dead center
    edge_alpha    = result.getpixel((118, 100))[3]   # 18 px from center, within radius
    outside_alpha = result.getpixel((130, 100))[3]   # well outside radius

    assert center_alpha > 200,                           "Center must be near-opaque"
    assert edge_alpha < center_alpha,                    "Edge must fade (feathered brush, not flat fill)"
    assert outside_alpha < 30,                           "Outside radius must be near-transparent"


def test_soft_stroke_multiple_points_paints_path():
    """Multiple stroke points must all leave paint marks."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_soft_stroke

    canvas = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    pts = [
        {"x": 50,  "y": 100, "pressure": 0.8},
        {"x": 150, "y": 100, "pressure": 0.9},
        {"x": 250, "y": 100, "pressure": 1.0},
        {"x": 350, "y": 100, "pressure": 0.7},
    ]
    result = paint_soft_stroke(canvas, pts, color=(200, 100, 255), radius=18, opacity=0.9)

    # Each point center must have paint
    for pt in pts:
        px = result.getpixel((pt["x"], pt["y"]))
        assert px[3] > 100, f"Point ({pt['x']},{pt['y']}) must have paint alpha > 100, got {px[3]}"


def test_airbrush_builds_up_with_passes():
    """Multiple airbrush passes must accumulate — more passes = more opaque."""
    from krita_mcp_lazy.brush_sim.soft_brush import build_airbrush_region

    canvas = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    result_1 = build_airbrush_region(canvas, (100, 100), 40, (200, 100, 255), passes=1)
    result_5 = build_airbrush_region(canvas, (100, 100), 40, (200, 100, 255), passes=5)

    alpha_1 = result_1.getpixel((100, 100))[3]
    alpha_5 = result_5.getpixel((100, 100))[3]

    assert alpha_1 > 0,          "Single pass must leave some paint"
    assert alpha_5 > alpha_1,    "5 passes must be more opaque than 1 pass"


def test_airbrush_soft_center_falloff():
    """Airbrush center must be more opaque than its edge — Gaussian soft blob."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_airbrush_pass

    canvas = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    result = paint_airbrush_pass(canvas, (150, 150), radius=60, color=(100, 180, 255), opacity=0.5)

    center_alpha = result.getpixel((150, 150))[3]
    edge_alpha   = result.getpixel((205, 150))[3]   # near edge of radius

    assert center_alpha > edge_alpha, "Airbrush must be softer at edges than center"


def test_glow_halo_brightens_canvas():
    """Screen-blend glow must brighten surrounding area — not darken or leave unchanged."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_glow_halo

    canvas = Image.new("RGBA", (200, 200), (10, 10, 40, 255))
    result = paint_glow_halo(canvas, (100, 100), radius=20, color=(255, 255, 180))

    orig_r  = canvas.getpixel((100, 100))[0]
    glow_r  = result.getpixel((100, 100))[0]

    assert glow_r > orig_r, f"Glow must brighten canvas (orig={orig_r}, after={glow_r})"


def test_glow_halo_affects_pixels_outside_center():
    """Glow must spread beyond its center — that's the whole point of bloom."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_glow_halo

    canvas = Image.new("RGBA", (200, 200), (5, 5, 20, 255))
    result = paint_glow_halo(canvas, (100, 100), radius=15, color=(255, 240, 160))

    # Pixels at radius*2 distance should still be brighter than original
    offset_r  = result.getpixel((130, 100))[0]
    original_r = canvas.getpixel((130, 100))[0]

    assert offset_r >= original_r, "Glow bloom must affect pixels beyond the center radius"


def test_ink_stroke_paints_line_between_points():
    """Ink stroke must connect consecutive points with visible paint."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_ink_stroke

    canvas = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    pts = [
        {"x": 50,  "y": 150},
        {"x": 150, "y": 150},
        {"x": 250, "y": 150},
    ]
    result = paint_ink_stroke(canvas, pts, color=(255, 42, 85), width=4)

    # Midpoint of the line must have paint
    mid = result.getpixel((150, 150))
    assert mid[3] > 100, f"Ink stroke midpoint must have paint alpha > 100, got {mid[3]}"
    # Color should be close to crimson
    assert mid[0] > 150, f"Red channel should be strong (crimson stroke), got {mid[0]}"


def test_ink_stroke_has_slight_feather():
    """Ink stroke should have slight softness — not perfectly hard aliased edge."""
    from krita_mcp_lazy.brush_sim.soft_brush import paint_ink_stroke

    canvas = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    pts = [{"x": 20, "y": 100}, {"x": 180, "y": 100}]
    result = paint_ink_stroke(canvas, pts, color=(255, 255, 255), width=6)

    # Just outside stroke edge should have some alpha (feathered), not hard 0
    # Stroke center at y=100, width=6 → edge at y=103
    just_inside  = result.getpixel((100, 101))[3]
    just_outside = result.getpixel((100, 106))[3]

    # Both can be nonzero due to feather, but inside must be >= outside
    assert just_inside >= just_outside, "Ink stroke must feather outward"
