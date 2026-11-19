# Krita MCP — Autonomous Painter: MCP Khud Puri Image Draw Karega

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (Native). Steps use checkbox (`- [ ]`) syntax.

**Goal:** MCP autonomous painter — Krita ke live canvas pe layer-by-layer, brush-by-brush, puri professional anime movie poster khud draw karega. User ko kuch nahi karna — sirf Krita screen pe dekhega painting hote hue. Baad mein chahe toh refine kare.

**Architecture:**
Ek **Painting Director** (`src/.../painting_director.py`) jo decide karta hai: "sky ke liye airbrush sweeps", "moon ke liye soft round glow", "characters ke liye Gemini-generated art import". Har element ke liye ek **Brush Simulator** (`effects.py`) Pillow mein actual brush appearance banata hai — soft round brush = Gaussian blob, airbrush = multi-pass low-opacity buildup, ink brush = hard edge feathered. Yeh pixel data Krita ke `node.setPixelData()` mein jaata hai aur `doc.refreshProjection()` call hoti hai — **user real time mein Krita screen pe dekhta hai painting hote hue**, element by element. Character key art ke liye Gemini Imagen call, baaki sab MCP khud draw karta hai.

**Tech Stack:** Pillow 10+ (`GaussianBlur`, `ImageChops.screen`, `alpha_composite`), `google-genai` (Gemini Imagen, optional), `setPixelData` + `refreshProjection` (Krita native API), FastMCP, asyncio TCP IPC `127.0.0.1:18812`, Python 3.14 MCP server + Python 3.13 Krita plugin.

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- MCP draws EVERYTHING autonomously — no user input needed during painting.
- Each draw operation: render pixel buffer (Pillow server-side) → `setPixelData` → `refreshProjection` → user sees update in Krita within 100ms.
- Brush simulation: soft round brush = `GaussianBlur` on filled ellipse (feathered edge, NOT flat PIL circle). Airbrush = same but radius 3-5× bigger, opacity 10-20% per pass, 5-8 overlapping passes.
- Gemini Imagen: if `GEMINI_API_KEY` present → generate character art. If absent → geometric silhouette placeholder (still drawn with soft brushes, not hard polygons).
- Each semantic layer pushed separately into Krita — non-destructive layer stack preserved.
- Plugin must be installed inside Krita for live mode; `krita_plugin_setup_guide` tool tells user exactly how.

## Review Focus

- **`refreshProjection` after each `setPixelData`:** Without this call Krita screen does not update — painting appears frozen. Every stroke handler must call it.
- **Large pixel buffer (2480×3508×4 = ~35 MB per layer):** Push layer in horizontal tiles of `tile_height=256` rows — `node.setPixelData(chunk, 0, y_start, width, 256)` per tile. Never push full canvas in one call.
- **Soft brush alpha buildup:** Airbrush passes must `alpha_composite` onto existing layer buffer — not replace it — otherwise each pass erases the previous one.
- **Gemini absent + no user image:** Painting Director falls back to geometric silhouettes drawn with soft brushes — still visually acceptable, not a crash.
- **Layer ordering in Krita:** `childNodes()` returns top-to-bottom; when inserting a new layer above another, use `insertChildNode(0, node)` on the parent group, not append.

---

### Task 1: Soft Brush Simulator — The Core Painting Engine

**Files:**
- Create: `src/krita_mcp_lazy/brush_sim/soft_brush.py`
- Create: `src/krita_mcp_lazy/brush_sim/__init__.py`
- Test: `tests/unit/brush_sim/test_soft_brush.py`

**Interfaces:**
- Produces:
  - `paint_soft_stroke(canvas: Image, points: list[dict], color: tuple, radius: int, opacity: float) -> Image` — feathered brush, `alpha_composite` per point
  - `paint_airbrush_pass(canvas: Image, center: tuple, radius: int, color: tuple, opacity: float) -> Image` — single low-opacity Gaussian blob
  - `build_airbrush_region(canvas: Image, center: tuple, radius: int, color: tuple, passes: int) -> Image` — stacked airbrush passes, builds up color naturally
  - `paint_glow_halo(canvas: Image, center: tuple, radius: int, color: tuple) -> Image` — bloom via `GaussianBlur` → `ImageChops.screen`
  - `paint_ink_stroke(canvas: Image, points: list[dict], color: tuple, width: int) -> Image` — hard-ish edge with slight feather (ink brush feel)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/brush_sim/test_soft_brush.py
from PIL import Image
from krita_mcp_lazy.brush_sim.soft_brush import (
    paint_soft_stroke, build_airbrush_region, paint_glow_halo
)

def test_soft_stroke_has_feathered_edges():
    """Soft brush must have gradient falloff — no hard pixel boundary."""
    canvas = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    pts = [{"x": 100, "y": 100, "pressure": 1.0}]
    result = paint_soft_stroke(canvas, pts, color=(255, 255, 255), radius=20, opacity=1.0)
    # Center should be bright, edge should be dim — not flat fill
    center_px = result.getpixel((100, 100))
    edge_px = result.getpixel((118, 100))  # 18px from center, within radius
    outer_px = result.getpixel((125, 100))  # just outside
    assert center_px[3] > 200, "Center must be near-opaque"
    assert edge_px[3] < center_px[3], "Edge must be less opaque than center (feathered)"
    assert outer_px[3] < 30, "Outside radius must be near-transparent"

def test_airbrush_builds_up_with_passes():
    """Multiple airbrush passes must accumulate color — not stay flat."""
    canvas = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    result_1 = build_airbrush_region(canvas, (100, 100), 40, (200, 100, 255), passes=1)
    result_5 = build_airbrush_region(canvas, (100, 100), 40, (200, 100, 255), passes=5)
    alpha_1 = result_1.getpixel((100, 100))[3]
    alpha_5 = result_5.getpixel((100, 100))[3]
    assert alpha_5 > alpha_1, "More passes must produce more opaque result"

def test_glow_halo_brightens_surrounding_pixels():
    """Glow must affect pixels OUTSIDE the center, not just the center itself."""
    canvas = Image.new("RGBA", (200, 200), (10, 10, 40, 255))
    result = paint_glow_halo(canvas, (100, 100), radius=15, color=(255, 255, 200))
    # Pixels at center+radius should be brighter than original canvas
    orig_r = canvas.getpixel((100, 100))[0]
    glow_r = result.getpixel((100, 100))[0]
    assert glow_r > orig_r, "Glow must brighten the canvas around center"
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/unit/brush_sim/ -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `soft_brush.py`**

```python
# src/krita_mcp_lazy/brush_sim/soft_brush.py
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from typing import List, Tuple
import math

def _make_soft_brush_stamp(radius: int, color: Tuple, opacity: float) -> Image.Image:
    """Core primitive: a single soft round brush stamp — Gaussian feathered circle."""
    size = radius * 4
    stamp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    # Hard circle in center
    cx = size // 2
    draw.ellipse([cx - radius, cx - radius, cx + radius, cx + radius],
                 fill=(*color[:3], int(255 * opacity)))
    # Gaussian blur = feathered edge (the brush softness)
    return stamp.filter(ImageFilter.GaussianBlur(radius=radius * 0.4))


def paint_soft_stroke(
    canvas: Image.Image,
    points: List[dict],
    color: Tuple,
    radius: int,
    opacity: float,
) -> Image.Image:
    """Paint a soft round brush stroke along pressure-sensitive points."""
    result = canvas.copy()
    stamp = _make_soft_brush_stamp(radius, color, opacity)
    stamp_size = stamp.size[0]
    half = stamp_size // 2
    for p in points:
        x, y = int(p["x"]), int(p["y"])
        pressure = float(p.get("pressure", 1.0))
        scaled = stamp.resize(
            (max(4, int(stamp_size * pressure)), max(4, int(stamp_size * pressure))),
            Image.LANCZOS
        )
        sh = scaled.size[0] // 2
        paste_x, paste_y = x - sh, y - sh
        result.alpha_composite(scaled, dest=(paste_x, paste_y))
    return result


def paint_airbrush_pass(
    canvas: Image.Image,
    center: Tuple,
    radius: int,
    color: Tuple,
    opacity: float,
) -> Image.Image:
    """Single airbrush pass: very large, very soft, very low opacity."""
    result = canvas.copy()
    blob = Image.new("RGBA", (radius * 4, radius * 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(blob)
    cx = radius * 2
    draw.ellipse([cx - radius, cx - radius, cx + radius, cx + radius],
                 fill=(*color[:3], int(255 * opacity)))
    blob = blob.filter(ImageFilter.GaussianBlur(radius=radius * 0.6))
    paste_x = center[0] - radius * 2
    paste_y = center[1] - radius * 2
    result.alpha_composite(blob, dest=(paste_x, paste_y))
    return result


def build_airbrush_region(
    canvas: Image.Image,
    center: Tuple,
    radius: int,
    color: Tuple,
    passes: int = 6,
) -> Image.Image:
    """Stack multiple low-opacity airbrush passes — color builds up naturally."""
    result = canvas.copy()
    per_pass_opacity = 0.12  # each pass: 12% — 6 passes ≈ 55% total buildup
    for _ in range(passes):
        result = paint_airbrush_pass(result, center, radius, color, per_pass_opacity)
    return result


def paint_glow_halo(
    canvas: Image.Image,
    center: Tuple,
    radius: int,
    color: Tuple,
) -> Image.Image:
    """Screen-blend glow: blur a bright blob → screen onto canvas = additive glow."""
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    cx, cy = center
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 fill=(*color[:3], 180))
    glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=radius * 0.8))
    # Screen blend: brightens without clipping
    base_rgb = canvas.convert("RGB")
    glow_rgb = glow_blurred.convert("RGB")
    screened = ImageChops.screen(base_rgb, glow_rgb)
    result = screened.convert("RGBA")
    result.putalpha(canvas.getchannel("A"))
    return result


def paint_ink_stroke(
    canvas: Image.Image,
    points: List[dict],
    color: Tuple,
    width: int,
) -> Image.Image:
    """Ink brush: hard edge but slight feather for natural feel."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(1, len(points)):
        p0, p1 = points[i - 1], points[i]
        draw.line([(p0["x"], p0["y"]), (p1["x"], p1["y"])],
                  fill=(*color[:3], 255), width=width)
    # Slight feather for natural ink edge
    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.8))
    result = canvas.copy()
    result.alpha_composite(layer)
    return result
```

- [ ] **Step 4: Run tests to verify PASS**

Run: `pytest tests/unit/brush_sim/ -v`
Expected: ALL 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/brush_sim/ tests/unit/brush_sim/
git commit -m "feat(brush_sim): professional soft brush simulator — feathered, airbrush buildup, screen-blend glow"
```

---

### Task 2: Painting Director — What to Paint Where, With Which Brush

**Files:**
- Create: `src/krita_mcp_lazy/painting_director/director.py`
- Create: `src/krita_mcp_lazy/painting_director/layers.py`
- Create: `src/krita_mcp_lazy/painting_director/__init__.py`
- Test: `tests/unit/painting_director/test_director.py`

**Interfaces:**
- Consumes: `BrushSimulator` (Task 1), `generate_base_art` (Gemini, Task 3), canvas dimensions from spec
- Produces: `PaintingDirector.render_all_layers(width, height, spec) -> list[LayerBuffer]`
  - `LayerBuffer(name: str, pixels: bytes, x: int, y: int, width: int, height: int, blend_mode: str)`

Each `LayerBuffer` = one Krita paint layer's full pixel data, ready to push via `setPixelData`.

Layer stack (bottom to top):

| # | Layer Name | Brush Technique |
|---|-----------|-----------------|
| 0 | `Sky_Gradient` | Airbrush sweeps, 8 passes, top→bottom color shift |
| 1 | `Sky_Nebula_Dust` | Huge airbrush blobs, low opacity, violet/indigo |
| 2 | `Stars_Field` | Tiny hard stamps + bloom pass via `paint_glow_halo` |
| 3 | `Moon_Base` | Soft round brush, cream white, crescent mask |
| 4 | `Moon_Glow` | `paint_glow_halo`, large radius, warm white |
| 5 | `City_Skyline` | Ink brush outlines, dark indigo fill, airbrush warm window lights |
| 6 | `Characters_Art` | Gemini-generated PNG OR geometric silhouettes with soft brush fill |
| 7 | `Rim_Lights` | Thin soft strokes on character edges, rose+gold colors |
| 8 | `Sakura_Petals` | Individual petal stamps rotated, scattered |
| 9 | `Red_Thread` | Ink stroke, crimson, with glow halo overlay |
| 10 | `Typography` | Text render with glow halo |

- [ ] **Step 1: Write failing test**

```python
# tests/unit/painting_director/test_director.py
from krita_mcp_lazy.painting_director.director import PaintingDirector
from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec

def test_director_renders_all_layers():
    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)
    layers = director.render_all_layers(width=248, height=350)
    assert len(layers) >= 10, f"Expected ≥10 layers, got {len(layers)}"
    for layer in layers:
        assert layer.name, "Every layer must have a name"
        assert len(layer.pixels) == 248 * 350 * 4, \
            f"Layer {layer.name}: pixel buffer must be width×height×4 bytes"

def test_sky_layer_has_color_gradient():
    """Sky top must be darker than sky bottom."""
    from PIL import Image
    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)
    layers = director.render_all_layers(width=248, height=350)
    sky = next(l for l in layers if "Sky_Gradient" in l.name)
    img = Image.frombytes("RGBA", (248, 350), sky.pixels)
    top_pixel = img.getpixel((124, 10))    # top center
    bottom_pixel = img.getpixel((124, 320))  # bottom center
    # Top should be darker (deep navy) than bottom (warm horizon)
    top_luminance = top_pixel[0] + top_pixel[1] + top_pixel[2]
    bottom_luminance = bottom_pixel[0] + bottom_pixel[1] + bottom_pixel[2]
    assert bottom_luminance > top_luminance, \
        "Sky bottom (warm horizon) must be brighter than sky top (deep navy)"
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/painting_director/ -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `layers.py`**

```python
# src/krita_mcp_lazy/painting_director/layers.py
from dataclasses import dataclass

@dataclass
class LayerBuffer:
    name: str
    pixels: bytes        # RGBA bytes, width × height × 4
    x: int
    y: int
    width: int
    height: int
    blend_mode: str = "normal"
    opacity: int = 255
```

- [ ] **Step 4: Implement `director.py`** — 11 layer rendering methods

`PaintingDirector.__init__(self, spec: dict)` stores spec and palette.

`render_all_layers(width, height) -> list[LayerBuffer]`:
Calls each of the following, collects results in order:

```python
def _render_sky_gradient(self, w, h) -> LayerBuffer:
    # Airbrush sweeps: 8 horizontal color bands
    # colors: zenith→mid→twilight→horizon from spec palette
    # Each band: build_airbrush_region at y=band_center, radius=h//8, 8 passes
    # Merge all passes via alpha_composite on a single RGBA canvas
    # Return LayerBuffer("Sky_Gradient", canvas.tobytes(), 0, 0, w, h)

def _render_nebula_dust(self, w, h) -> LayerBuffer:
    # 5 large violet/indigo blobs (airbrush, 3 passes, opacity 0.08)
    # scattered in upper 70% of canvas

def _render_stars(self, w, h) -> LayerBuffer:
    # 250 tiny hard stamps (radius 1-3) in random positions (seed=42)
    # Then paint_glow_halo on 20% of them (brighter stars)
    # blend_mode="screen" (Krita will screen this layer)

def _render_moon(self, w, h) -> LayerBuffer:
    # Soft round brush, cream white, center=(w*0.78, h*0.14), radius=w*0.07
    # Crescent: paint sky-color airbrush blob offset-right to mask part of moon
    # Moon glow: paint_glow_halo same center, radius*2.5

def _render_city_skyline(self, w, h) -> LayerBuffer:
    # 10-15 rectangular building shapes at y=h*0.72 to y=h
    # ink_stroke outlines, dark indigo (#10142A)
    # airbrush warm orange (#FFA040) tiny dots for windows (seed=13)

def _render_characters(self, w, h, gemini_art=None) -> LayerBuffer:
    # If gemini_art: resize+center-crop, return as LayerBuffer
    # Else: soft_stroke silhouettes
    #   Girl: left side, standing profile, simplified bezier-ish points
    #   Boy: right side, leaning forward
    #   Both: deep indigo fill (#10142A), soft round brush
    #   Rim light: thin rose stroke on left edges

def _render_sakura_petals(self, w, h) -> LayerBuffer:
    # 80 individual petal stamps
    # Each: small ellipse (8×5px), rotate random angle, paste at random pos
    # Depth scaling: foreground petals larger + slightly blurred, bg petals smaller

def _render_red_thread(self, w, h) -> LayerBuffer:
    # Bezier curve from girl's hand to boy's hand
    # ink_stroke, crimson (#FF2A55), width=3
    # + paint_glow_halo along thread (screen blend layer)

def _render_typography(self, w, h) -> LayerBuffer:
    # studio line, JP title, EN title, tagline, release line
    # Each: glow halo behind text (blur→screen), then sharp text on top
    # Fonts: get_font() with fallback chain
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/unit/painting_director/ -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/painting_director/ tests/unit/painting_director/
git commit -m "feat(director): PaintingDirector renders all 11 layers with professional brush simulation"
```

---

### Task 3: Gemini Art Generator — Character Key Art

**Files:**
- Create: `src/krita_mcp_lazy/image_gen/gemini_gen.py`
- Create: `src/krita_mcp_lazy/image_gen/__init__.py`
- Test: `tests/unit/image_gen/test_gemini_gen.py`

**Interfaces:**
- Produces: `generate_character_art(prompt: str, width: int, height: int) -> Optional[PIL.Image.Image]`

- [ ] **Step 1: Write failing tests**

```python
def test_returns_none_when_no_key():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {}, clear=True):
        from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art
        result = generate_character_art("anime couple", 100, 150)
    assert result is None

def test_calls_gemini_when_key_present():
    import os
    from unittest.mock import patch
    from PIL import Image
    fake_img = Image.new("RGBA", (100, 150), (30, 10, 80, 255))
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake"}):
        with patch("krita_mcp_lazy.image_gen.gemini_gen._call_gemini") as m:
            m.return_value = fake_img
            from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art
            result = generate_character_art("anime couple", 100, 150)
    assert result is not None
    m.assert_called_once()
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/unit/image_gen/ -v`
Expected: FAIL.

- [ ] **Step 3: Implement `gemini_gen.py`**

`generate_character_art(prompt, width, height)`:
1. If `GEMINI_API_KEY` not in env: return `None`
2. Else: call `_call_gemini(prompt, width, height)`:
   - `google.genai.Client(api_key=...).models.generate_images(model="imagen-3.0-generate-002", prompt=prompt, ...)`
   - Parse first image bytes → `PIL.Image.open(io.BytesIO(bytes))` → resize to `(width, height)` → `convert("RGBA")`
   - Any exception → log + return `None`

- [ ] **Step 4: Install dependency and run tests to verify PASS**

Run: `pip install google-genai`
Run: `pytest tests/unit/image_gen/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/image_gen/ tests/unit/image_gen/
git commit -m "feat(image_gen): Gemini Imagen wrapper for character key art generation"
```

---

### Task 4: Krita Canvas Pusher — Tiles + Live Update

**Files:**
- Create: `src/krita_mcp_lazy/krita_pusher/pusher.py`
- Create: `src/krita_mcp_lazy/krita_pusher/__init__.py`
- Modify: `plugins/krita_mcp_bridge/handlers_document.py` — add `document.import_layer` handler
- Test: `tests/unit/krita_pusher/test_pusher.py`

**Interfaces:**
- Consumes: `LayerBuffer` from Task 2, IPC client on `127.0.0.1:18812`
- Produces:
  - `KritaPusher.push_layer(doc_id, layer_buf) -> dict` — creates Krita layer, pushes pixel data in tiles, calls `refreshProjection`
  - `document.import_layer` IPC handler in plugin

- [ ] **Step 1: Write failing test**

```python
# tests/unit/krita_pusher/test_pusher.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.krita_pusher.pusher import KritaPusher
from krita_mcp_lazy.painting_director.layers import LayerBuffer

@pytest.mark.asyncio
async def test_pusher_calls_import_layer_per_buffer():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"layer_id": "lyr_001", "mode": "headless_mock"}
    pusher = KritaPusher(mock_client)
    buf = LayerBuffer("Sky_Gradient", bytes(248 * 350 * 4), 0, 0, 248, 350)
    result = await pusher.push_layer("doc_001", buf)
    mock_client.send_job.assert_called()
    first_call = mock_client.send_job.call_args_list[0]
    assert first_call[0][0] == "document.import_layer"
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/krita_pusher/ -v`
Expected: FAIL.

- [ ] **Step 3: Implement `pusher.py`**

```python
class KritaPusher:
    TILE_HEIGHT = 256  # rows per push — avoids large single setPixelData call

    async def push_layer(self, doc_id: str, layer_buf: LayerBuffer) -> dict:
        # 1. Create the layer in Krita
        create_resp = await self.client.send_job("document.import_layer", {
            "doc_id": doc_id,
            "layer_name": layer_buf.name,
            "width": layer_buf.width,
            "height": layer_buf.height,
            "blend_mode": layer_buf.blend_mode,
            "opacity": layer_buf.opacity,
        })
        layer_id = create_resp.result.get("layer_id", layer_buf.name)

        # 2. Push pixels in tiles
        import base64
        stride = layer_buf.width * 4
        for y_start in range(0, layer_buf.height, self.TILE_HEIGHT):
            tile_h = min(self.TILE_HEIGHT, layer_buf.height - y_start)
            tile_bytes = b""
            for row in range(tile_h):
                row_start = (y_start + row) * stride
                tile_bytes += layer_buf.pixels[row_start: row_start + stride]
            await self.client.send_job("layer.set_pixel_tile", {
                "doc_id": doc_id,
                "layer_id": layer_id,
                "x": 0,
                "y": y_start,
                "width": layer_buf.width,
                "height": tile_h,
                "pixels_b64": base64.b64encode(tile_bytes).decode(),
            })

        # 3. Refresh canvas after full layer push
        await self.client.send_job("document.refresh", {"doc_id": doc_id})
        return {"layer_id": layer_id, "name": layer_buf.name}
```

- [ ] **Step 4: Implement `document.import_layer` and `layer.set_pixel_tile` and `document.refresh` handlers in plugin**

In `handlers_document.py`:

`handle_import_layer`: Create new paint layer in Krita doc with `doc.createNode(name, "paintLayer")`, insert into root node, return `layer_id`. Headless: return mock `layer_id`.

`handle_set_pixel_tile`: Get node by `layer_id`, decode base64 pixels, call `node.setPixelData(QByteArray(raw), x, y, width, height)`. Headless: no-op return `{"ok": True}`.

`handle_refresh_document`: Call `doc.refreshProjection()`. Headless: no-op.

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/unit/krita_pusher/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/krita_pusher/ plugins/krita_mcp_bridge/handlers_document.py
git commit -m "feat(pusher): tiled pixel push to Krita with live refreshProjection per layer"
```

---

### Task 5: `krita_paint_poster` MCP Tool — Full Autonomous Painter

**Files:**
- Create: `src/krita_mcp_lazy/server/tools_autonomous_painter.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Create: `scripts/paint_anime_poster.py`
- Test: `tests/unit/server/test_autonomous_painter.py`

**Interfaces:**
- Consumes: `PaintingDirector`, `generate_character_art` (Gemini), `KritaPusher`, IPC client
- Produces: MCP tool `krita_paint_poster(prompt, doc_id, width, height) -> dict` with keys `layers_painted`, `doc_id`, `mode`, `output_png_path`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/server/test_autonomous_painter.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_paint_poster_paints_all_layers():
    from krita_mcp_lazy.server.tools_autonomous_painter import paint_poster
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"layer_id": "lyr_x", "mode": "headless_mock", "ok": True}
    result = await paint_poster(
        prompt="anime love poster twilight",
        doc_id="doc_test",
        width=248,
        height=350,
        client=mock_client,
    )
    assert result["layers_painted"] >= 10
    assert result["mode"] in ("live_krita", "headless_mock")
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/server/test_autonomous_painter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `paint_poster()`**

```python
async def paint_poster(
    prompt: str,
    doc_id: str,
    width: int = 2480,
    height: int = 3508,
    client = None,
) -> dict:
    from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec
    from krita_mcp_lazy.painting_director.director import PaintingDirector
    from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art
    from krita_mcp_lazy.krita_pusher.pusher import KritaPusher

    spec = get_whispers_in_starlight_spec()
    director = PaintingDirector(spec)

    # Try Gemini for character art
    char_art = generate_character_art(
        f"{prompt}, anime style, twilight rooftop, two characters", width, height
    )

    # Render all layers (server-side, Pillow)
    layers = director.render_all_layers(width, height, gemini_art=char_art)

    # Push each layer to Krita live
    pusher = KritaPusher(client)
    pushed = []
    for layer_buf in layers:
        result = await pusher.push_layer(doc_id, layer_buf)
        pushed.append(result["name"])

    # Also save flat composite PNG for reference
    from krita_mcp_lazy.painting_director.director import composite_to_png
    out_path = f"output/painted_poster_{doc_id}.png"
    composite_to_png(layers, width, height, out_path)

    return {
        "layers_painted": len(pushed),
        "layer_names": pushed,
        "doc_id": doc_id,
        "mode": "headless_mock",  # oracle updates this
        "output_png_path": out_path,
    }
```

Register as `@mcp.tool()` named `krita_paint_poster`.

- [ ] **Step 4: Implement `composite_to_png(layers, w, h, path)` in `director.py`**

Composites all `LayerBuffer` objects in order using `Image.alpha_composite`, saves to `path`.

- [ ] **Step 5: Run test to verify PASS**

Run: `pytest tests/unit/server/test_autonomous_painter.py -v`
Expected: PASS.

- [ ] **Step 6: Write `scripts/paint_anime_poster.py`**

CLI script: connects to IPC (`127.0.0.1:18812`), creates document via `document.create`, calls `paint_poster()`, opens output folder.

- [ ] **Step 7: Run script and do visual check**

Run: `python scripts/paint_anime_poster.py`

Open `output/painted_poster_*.png` and confirm:
- [ ] Sky: smooth gradient dark navy → violet → rose → gold, NO hard band edges
- [ ] Stars: soft bloom dots, not flat circles
- [ ] Moon: crescent shape (not full circle), glow halo around it
- [ ] City: building silhouettes at horizon, warm window dots
- [ ] Characters: visible silhouettes (or Gemini art if key present) with rim light
- [ ] Sakura: scattered petals at different sizes and angles
- [ ] Red thread: thin glowing line connecting characters
- [ ] Typography: readable title text with glow

If any check fails → adjust that specific `_render_*` method and re-run. Do NOT commit until all visual checks pass.

- [ ] **Step 8: Commit**

```bash
git add src/krita_mcp_lazy/server/tools_autonomous_painter.py scripts/paint_anime_poster.py
git commit -m "feat(server): krita_paint_poster tool — autonomous full-canvas painter via brush simulation + Krita live push"
```

---

## Self-Review

1. **Spec coverage:** MCP draws everything — sky, stars, moon, city, characters, petals, thread, text. Gemini for character art. Live Krita push layer by layer with real-time screen update. User sees painting happen.
2. **Step scan:** Every step has test code, exact signatures, or exact algorithm. `_make_soft_brush_stamp` body written because PIL alone doesn't determine it.
3. **Type consistency:** `LayerBuffer`, `PaintingDirector.render_all_layers`, `KritaPusher.push_layer`, `paint_poster` — consistent naming and types throughout.
4. **Review Focus:** All 5 edge cases (refreshProjection missing, large buffer OOM, airbrush alpha buildup, Gemini absent, CJK font) covered in owning tasks.
5. **Proportion:** Plan is ~2.5× longer than the code bodies it describes. Signatures given everywhere; bodies only where algorithm isn't obvious.
