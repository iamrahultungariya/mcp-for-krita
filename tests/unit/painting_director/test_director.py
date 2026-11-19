"""Tests for the PaintingDirector and layer generation."""
import os
import pytest
from PIL import Image

from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec


def test_director_renders_all_layers():
    """Director must produce at least 10 named semantic LayerBuffer items."""
    from krita_mcp_lazy.painting_director.director import PaintingDirector

    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)
    layers = director.render_all_layers(width=248, height=350)

    assert len(layers) >= 10, f"Expected >= 10 layers, got {len(layers)}"
    for layer in layers:
        assert layer.name, "Every layer must have a name"
        assert len(layer.pixels) == 248 * 350 * 4, (
            f"Layer {layer.name}: pixel buffer must be width*height*4 bytes ({248*350*4}), got {len(layer.pixels)}"
        )


def test_sky_layer_has_color_gradient():
    """Sky top must be darker (zenith navy) than sky bottom (warm twilight/horizon)."""
    from krita_mcp_lazy.painting_director.director import PaintingDirector

    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)
    layers = director.render_all_layers(width=248, height=350)

    sky = next(l for l in layers if "Sky_Gradient" in l.name)
    img = Image.frombytes("RGBA", (248, 350), sky.pixels)

    top_pixel = img.getpixel((124, 15))      # upper area
    bottom_pixel = img.getpixel((124, 300))  # lower horizon area

    top_lum = top_pixel[0] + top_pixel[1] + top_pixel[2]
    bottom_lum = bottom_pixel[0] + bottom_pixel[1] + bottom_pixel[2]

    assert bottom_lum > top_lum, (
        f"Sky bottom horizon ({bottom_lum}) must be brighter than top midnight ({top_lum})"
    )


def test_composite_to_png(tmp_path):
    """composite_to_png should merge layer buffers and save a valid PNG file."""
    from krita_mcp_lazy.painting_director.director import PaintingDirector, composite_to_png

    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)
    layers = director.render_all_layers(width=248, height=350)

    out_file = str(tmp_path / "composite_test.png")
    composite_to_png(layers, 248, 350, out_file)

    assert os.path.exists(out_file), "Output PNG must be created"
    saved_img = Image.open(out_file)
    assert saved_img.size == (248, 350)
    unique_colors = len(set(saved_img.getdata()))
    assert unique_colors > 100, f"Composite image must have rich color variety, got {unique_colors}"
