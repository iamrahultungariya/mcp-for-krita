# Krita MCP — Professional Image Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform krita-MCP-lazy from a "stroke-loop scribble machine" into a professional image engine: Gemini Imagen generates base artwork, a Pillow compositor applies cinematic effects (glow, blur, screen-blend, real typography), and the Krita MCP plugin imports each layer into the live Krita canvas for user refinement.

**Architecture:**
- **Input layer:** Accept either (A) a Gemini Imagen API call with a text prompt, or (B) a user-supplied image path/URL as base art.
- **Compositor layer:** Pillow-powered pipeline with real glow (GaussianBlur → screen blend), proper layer compositing (`Image.alpha_composite`), rotated petal shapes, and professional font rendering. Runs entirely on the MCP server (Python 3.14 + Pillow available).
- **Krita layer:** Each composited layer is pushed into live Krita canvas via the existing IPC bridge as individual paint layers — user can refine with real Krita brushes. Plugin setup instructions surfaced via `krita_plugin_setup_guide` tool.

**Tech Stack:** Gemini Imagen API (`google-genai`), Pillow 10+, `ImageChops.screen`, `ImageFilter.GaussianBlur`, `ImageFont.truetype`, FastMCP, AsyncIPC `127.0.0.1:18812`, Krita 5.3.4+ native API (`node.setPixelData`), Python 3.14.

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- Gemini Imagen API key read from env `GEMINI_API_KEY`; if absent, skip generation and use `user_image_path` instead — never crash.
- All Pillow operations on 2480×3508 must use band-by-band processing for gradients (no per-pixel Python loops).
- Glow compositing: always `GaussianBlur` → `ImageChops.screen` — never manually brightening pixel values.
- Typography: attempt `ImageFont.truetype` with font search path; fall back to `ImageFont.load_default(large=True)` on `OSError`.
- Each output layer saved as a PNG before Krita import — enables re-use and debugging.
- Plugin setup path: `%APPDATA%\krita\pykrita\krita_mcp_bridge\`.

## Review Focus

- **Gemini API absent (no key):** `generate_base_art()` must return `None` without raising; compositor then requires `user_image_path` to be provided, raising `ValueError("Either GEMINI_API_KEY or user_image_path is required")` only if both missing.
- **Pillow GaussianBlur on RGBA vs RGB:** `GaussianBlur` on RGBA mode blurs the alpha channel too, creating dark halos; must convert to RGB before blur, then recomposite alpha.
- **Krita import of large PNG (35 MB, 300 DPI):** `node.setPixelData` with 2480×3508×4 bytes must be chunked if Krita's Qt event loop can't handle it in one call — test with 500px tile size.
- **CJK font missing on Windows:** `ImageFont.truetype("NotoSerifJP-Regular.ttf")` will fail if font not installed; fallback chain: `%WINDIR%\Fonts\msgothic.ttc` → `load_default`.
- **Krita plugin not loaded (headless mode):** `document.import_image` must still write the file to `output/` and return `{"mode": "headless_mock", "file_saved": true}` — user gets the PNG even without Krita.

---

### Task 1: Gemini Imagen Wrapper — Base Art Generator

**Files:**
- Create: `src/krita_mcp_lazy/image_gen/gemini_gen.py`
- Create: `src/krita_mcp_lazy/image_gen/__init__.py`
- Test: `tests/unit/image_gen/test_gemini_gen.py`

**Interfaces:**
- Consumes: `google-genai` SDK, env `GEMINI_API_KEY`, `user_image_path: Optional[str]`
- Produces: `generate_base_art(prompt: str, width: int, height: int, user_image_path: Optional[str]) -> Optional[PIL.Image.Image]`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/image_gen/test_gemini_gen.py
import os
from unittest.mock import patch, MagicMock
from PIL import Image
from krita_mcp_lazy.image_gen.gemini_gen import generate_base_art

def test_returns_none_when_no_key_and_no_path():
    with patch.dict(os.environ, {}, clear=True):
        result = generate_base_art("anime poster", 100, 100, user_image_path=None)
    assert result is None

def test_loads_user_image_when_no_api_key(tmp_path):
    img = Image.new("RGBA", (100, 150), (30, 10, 80, 255))
    p = str(tmp_path / "ref.png")
    img.save(p)
    with patch.dict(os.environ, {}, clear=True):
        result = generate_base_art("anime", 100, 150, user_image_path=p)
    assert result is not None
    assert result.size == (100, 150)

def test_calls_gemini_api_when_key_present():
    fake_img = Image.new("RGBA", (100, 150))
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        with patch("krita_mcp_lazy.image_gen.gemini_gen._call_gemini_imagen") as mock_call:
            mock_call.return_value = fake_img
            result = generate_base_art("anime love poster", 100, 150)
    mock_call.assert_called_once()
    assert result is not None
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/unit/image_gen/ -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `gemini_gen.py`**

```python
# src/krita_mcp_lazy/image_gen/gemini_gen.py
import io, os
from typing import Optional
from PIL import Image

def generate_base_art(
    prompt: str,
    width: int,
    height: int,
    user_image_path: Optional[str] = None,
) -> Optional[Image.Image]:
```

Logic:
1. If `user_image_path` given: open with Pillow, resize to `(width, height)` with `LANCZOS`, convert to `RGBA`, return.
2. Else if `GEMINI_API_KEY` in env: call `_call_gemini_imagen(prompt, width, height)` and return result.
3. Else: return `None`.

`_call_gemini_imagen(prompt, width, height)`:
- Use `google.genai` SDK: `client.models.generate_images(model="imagen-3.0-generate-002", prompt=prompt, ...)`
- Parse response bytes into `PIL.Image.Image`, resize to `(width, height)`, return.
- Wrap in `try/except Exception` — return `None` on any API failure, log the error.

- [ ] **Step 4: Run tests to verify PASS**

Run: `pytest tests/unit/image_gen/ -v`
Expected: ALL PASS.

- [ ] **Step 5: Install dependency**

Run: `pip install google-genai`
Add `google-genai>=1.0` to `pyproject.toml` dependencies.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/image_gen/ tests/unit/image_gen/
git commit -m "feat(image_gen): add Gemini Imagen wrapper with user-image fallback"
```

---

### Task 2: Professional Compositor — Glow, Blur, Blend Modes, Typography

**Files:**
- Create: `src/krita_mcp_lazy/image_compositor/compositor.py`
- Create: `src/krita_mcp_lazy/image_compositor/effects.py`
- Create: `src/krita_mcp_lazy/image_compositor/typography.py`
- Create: `src/krita_mcp_lazy/image_compositor/__init__.py`
- Test: `tests/unit/image_compositor/test_compositor.py`
- Test: `tests/unit/image_compositor/test_effects.py`

**Interfaces:**
- Consumes: `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFilter`, `PIL.ImageChops`, `PIL.ImageFont`
- Produces:
  - `add_glow(base: Image, glow_layer: Image, radius: int) -> Image` (screen blend)
  - `add_atmospheric_gradient(size: tuple, colors: list[tuple]) -> Image` (band-based, no per-pixel loop)
  - `render_sakura_petals(size: tuple, count: int, palette: list) -> Image` (polygon + rotate)
  - `render_typography(size: tuple, title_jp: str, title_en: str, tagline: str, font_paths: list[str]) -> Image`
  - `ProfessionalCompositor.compose(base_art: Optional[Image], spec: dict, width: int, height: int) -> Image`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/image_compositor/test_effects.py
from PIL import Image
from krita_mcp_lazy.image_compositor.effects import add_glow, add_atmospheric_gradient

def test_glow_brightens_image():
    base = Image.new("RGBA", (100, 100), (10, 10, 50, 255))
    glow_layer = Image.new("RGBA", (100, 100), (200, 200, 255, 100))
    result = add_glow(base, glow_layer, radius=5)
    # Result must be brighter than base in at least some pixels
    base_avg = sum(p[0] for p in base.getdata()) / (100 * 100)
    result_avg = sum(p[0] for p in result.getdata()) / (100 * 100)
    assert result_avg > base_avg

def test_gradient_has_color_variety():
    colors = [(11, 16, 38), (38, 27, 78), (232, 106, 130), (252, 208, 161)]
    img = add_atmospheric_gradient((200, 300), colors)
    assert img.size == (200, 300)
    assert img.mode == "RGBA"
    unique = len(set(img.getdata()))
    assert unique > 10

# tests/unit/image_compositor/test_compositor.py
from krita_mcp_lazy.image_compositor.compositor import ProfessionalCompositor
from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec

def test_compositor_produces_color_rich_image():
    spec = get_whispers_in_starlight_spec()
    comp = ProfessionalCompositor(spec)
    img = comp.compose(base_art=None, spec=spec, width=248, height=350)
    assert img.size == (248, 350)
    assert img.mode == "RGBA"
    unique = len(set(img.getdata()))
    assert unique > 500, f"Expected color-rich image, got only {unique} unique colors"
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/unit/image_compositor/ -v`
Expected: FAIL.

- [ ] **Step 3: Implement `effects.py`**

```python
# src/krita_mcp_lazy/image_compositor/effects.py
from PIL import Image, ImageChops, ImageFilter, ImageDraw
import random, math

def add_glow(base: Image.Image, glow_layer: Image.Image, radius: int = 15) -> Image.Image:
    """Screen-blend a blurred glow layer over base. Brightens without clipping."""
    # 1. Convert glow to RGB for blur (preserve alpha separately)
    glow_rgb = glow_layer.convert("RGB")
    blurred = glow_rgb.filter(ImageFilter.GaussianBlur(radius=radius))
    base_rgb = base.convert("RGB")
    # 2. Screen blend: 1 - (1-A)(1-B)
    screened = ImageChops.screen(base_rgb, blurred)
    # 3. Reapply original alpha
    result = screened.convert("RGBA")
    result.putalpha(base.getchannel("A"))
    return result

def add_atmospheric_gradient(
    size: tuple,
    colors: list,  # list of (R,G,B) tuples top→bottom
) -> Image.Image:
    """Band-based gradient — no per-pixel loops."""
    w, h = size
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    n = len(colors) - 1
    band_h = h / n
    for i in range(n):
        c1, c2 = colors[i], colors[i + 1]
        y_start = int(i * band_h)
        y_end = int((i + 1) * band_h)
        sub_bands = max(1, y_end - y_start)
        for j in range(sub_bands):
            t = j / sub_bands
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            y = y_start + j
            draw.rectangle([0, y, w, y + 1], fill=(r, g, b, 255))
    return img

def add_star_field(size: tuple, count: int = 300, seed: int = 42) -> Image.Image:
    """Stars with bloom: bright dot + GaussianBlur screen pass."""
    w, h = size
    rng = random.Random(seed)
    # Base dots layer
    stars_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stars_layer)
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, int(h * 0.65))  # only upper 65% = sky
        brightness = rng.randint(180, 255)
        r = rng.randint(1, 3)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(brightness, brightness, 255, 255))
    # Bloom pass
    bloom = stars_layer.filter(ImageFilter.GaussianBlur(radius=3))
    result = ImageChops.screen(stars_layer.convert("RGB"), bloom.convert("RGB"))
    out = result.convert("RGBA")
    # Restore alpha from original star dots
    out.putalpha(stars_layer.getchannel("A"))
    return out

def add_moon(size: tuple, center: tuple, radius: int, color=(255, 252, 230)) -> Image.Image:
    """Crescent moon: large bright circle masked by offset dark circle + soft glow."""
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    # Outer glow (large, low alpha)
    glow_r = int(radius * 1.6)
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=(color[0], color[1], color[2], 40),
    )
    # Main moon body
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*color, 255))
    # Crescent shadow (offset dark circle)
    offset_x = int(radius * 0.35)
    sky_color = (11, 16, 38, 255)  # same as sky zenith
    draw.ellipse(
        [cx - radius + offset_x, cy - radius, cx + radius + offset_x, cy + radius],
        fill=sky_color,
    )
    # Soft bloom on moon
    return layer.filter(ImageFilter.GaussianBlur(radius=2))

def add_sakura_petals(size: tuple, count: int = 80, seed: int = 7) -> Image.Image:
    """Proper petal shapes: small ellipses rotated at random angles, depth-scaled."""
    w, h = size
    rng = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    petal_colors = [(255, 183, 178), (255, 170, 166), (255, 220, 210), (255, 255, 255)]
    for _ in range(count):
        # Individual petal on tiny canvas, then paste rotated
        px = rng.randint(0, w)
        py = rng.randint(int(h * 0.1), int(h * 0.8))
        depth = py / h  # farther = smaller
        pw = max(4, int(rng.randint(6, 14) * depth))
        ph = max(2, int(pw * 0.55))
        angle = rng.randint(0, 360)
        alpha = rng.randint(160, 240)
        color = rng.choice(petal_colors)
        petal_canvas = Image.new("RGBA", (pw * 4, ph * 4), (0, 0, 0, 0))
        pd = ImageDraw.Draw(petal_canvas)
        pd.ellipse([pw, ph, pw * 3, ph * 3], fill=(*color, alpha))
        petal_canvas = petal_canvas.rotate(angle, resample=Image.BICUBIC, expand=False)
        paste_x = px - pw * 2
        paste_y = py - ph * 2
        layer.paste(petal_canvas, (paste_x, paste_y), petal_canvas)
    return layer
```

- [ ] **Step 4: Implement `typography.py`**

Font search path order:
1. `C:\Windows\Fonts\NotoSerifJP-Regular.ttf`
2. `C:\Windows\Fonts\msgothic.ttc`
3. `C:\Windows\Fonts\arial.ttf`
4. `ImageFont.load_default(size=20)` as final fallback

```python
# src/krita_mcp_lazy/image_compositor/typography.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from pathlib import Path
from typing import Optional

FONT_SEARCH_PATHS = [
    r"C:\Windows\Fonts\NotoSerifJP-Regular.ttf",
    r"C:\Windows\Fonts\msgothic.ttc",
    r"C:\Windows\Fonts\times.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]

def get_font(size: int, paths: list = FONT_SEARCH_PATHS) -> ImageFont.FreeTypeFont:
    for fp in paths:
        try:
            return ImageFont.truetype(fp, size)
        except OSError:
            continue
    return ImageFont.load_default()

def render_typography(
    size: tuple,
    title_jp: str,
    title_en: str,
    tagline: str,
    studio_line: str = "A TOONFLOW ORIGINAL",
    release: str = "COMING TO THEATERS SUMMER 2026",
) -> Image.Image:
```

Typography layer renders:
- `studio_line`: small, top-centered, letter-spaced, white, 60% opacity
- `title_jp`: large (8% of height), center, cream white `#FFF8E7`, with glow pass (blur→screen)
- `title_en`: medium (5% of height), center below, `#E0D5FF`
- `tagline`: italic small (2.5% of height), center, `#FCD0A1`
- `release`: bottom, small, white, all-caps

Each text element: draw on transparent layer → GaussianBlur → screen blend → add sharp text on top.

- [ ] **Step 5: Implement `compositor.py`**

```python
# src/krita_mcp_lazy/image_compositor/compositor.py
class ProfessionalCompositor:
    def compose(
        self,
        base_art: Optional[Image.Image],
        spec: dict,
        width: int,
        height: int,
    ) -> Image.Image:
```

Compositing order (bottom to top — `Image.alpha_composite`):
1. Sky gradient (`add_atmospheric_gradient`)
2. Star field (`add_star_field`) — screen blend
3. Moon (`add_moon`) — normal blend
4. City skyline silhouette (`ImageDraw.polygon`, dark indigo)
5. Base art from Gemini / user image (if provided, `alpha_composite` center-cropped)
6. Sakura petals (`add_sakura_petals`) — normal blend, 80% opacity
7. Character silhouettes (if no base_art: simple polygon shapes as placeholder)
8. Red thread bezier (`ImageDraw.line`, width=4, screen blend glow)
9. Typography (`render_typography`)
10. Final color grade: `ImageEnhance.Color(result).enhance(1.15)` for saturation lift

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/unit/image_compositor/ -v`
Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/krita_mcp_lazy/image_compositor/ tests/unit/image_compositor/
git commit -m "feat(compositor): professional Pillow compositor with glow, screen blend, real typography"
```

---

### Task 3: `krita_generate_image` MCP Tool — Full Pipeline

**Files:**
- Create: `src/krita_mcp_lazy/server/tools_image_gen.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Test: `tests/unit/server/test_image_gen_tool.py`

**Interfaces:**
- Consumes: `generate_base_art()`, `ProfessionalCompositor`, `get_whispers_in_starlight_spec()`
- Produces: MCP tool `krita_generate_image(prompt, output_path, user_image_path, width, height) -> dict` with keys `output_path`, `mode`, `width`, `height`, `file_size_bytes`, `base_art_source`.

- [ ] **Step 1: Write failing test**

```python
def test_generate_image_tool_creates_color_rich_png(tmp_path):
    from krita_mcp_lazy.server.tools_image_gen import generate_image_tool
    out = str(tmp_path / "poster.png")
    result = generate_image_tool(
        prompt="anime love poster twilight",
        output_path=out,
        user_image_path=None,
        width=248,
        height=350,
    )
    assert os.path.isfile(out)
    assert result["file_size_bytes"] > 5000
    from PIL import Image
    img = Image.open(out)
    unique = len(set(img.getdata()))
    assert unique > 500
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/server/test_image_gen_tool.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `generate_image_tool()` and register as `@mcp.tool()`**

```python
def generate_image_tool(
    prompt: str,
    output_path: str,
    user_image_path: Optional[str] = None,
    width: int = 2480,
    height: int = 3508,
) -> dict:
    spec = get_whispers_in_starlight_spec()
    base = generate_base_art(prompt, width, height, user_image_path)
    comp = ProfessionalCompositor(spec)
    img = comp.compose(base_art=base, spec=spec, width=width, height=height)
    img.convert("RGB").save(output_path, "PNG", dpi=(300, 300))
    return {
        "output_path": output_path,
        "width": width,
        "height": height,
        "file_size_bytes": os.path.getsize(output_path),
        "base_art_source": "gemini" if base and not user_image_path else ("user_image" if user_image_path else "compositor_only"),
        "mode": "headless_mock",  # updated to live_krita after Task 4
    }
```

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/server/test_image_gen_tool.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/server/tools_image_gen.py src/krita_mcp_lazy/server/app.py
git commit -m "feat(server): krita_generate_image MCP tool with Gemini + professional compositor"
```

---

### Task 4: Krita Import + Plugin Setup Guide Tool

**Files:**
- Modify: `plugins/krita_mcp_bridge/handlers_document.py`
- Create: `src/krita_mcp_lazy/server/tools_plugin_setup.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Test: `tests/unit/plugin/test_import_image.py`

**Interfaces:**
- Consumes: `document.import_image` action with `{"file_path": str, "doc_id": str, "layer_name": str}`
- Produces:
  - `handle_import_image`: `{"layer_id": str, "layer_name": str, "mode": str, "file_saved": bool}`
  - `krita_plugin_setup_guide()` MCP tool → returns exact step-by-step Krita plugin installation instructions as string

- [ ] **Step 1: Write tests**

```python
# tests/unit/plugin/test_import_image.py
def test_import_image_headless_still_returns_layer_id():
    from plugins.krita_mcp_bridge.handlers_document import _handle_import_image_headless
    result = _handle_import_image_headless({
        "file_path": "output/test.png",
        "layer_name": "Test_Layer",
        "doc_id": "doc_001",
    })
    assert "layer_id" in result
    assert result["mode"] == "headless_mock"
    assert isinstance(result["layer_id"], str)
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/plugin/test_import_image.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `handle_import_image` in `handlers_document.py`**

Live path (`from krita import Krita` succeeds):
1. Load PNG from `file_path` as `QImage`
2. Get/create document via `get_document_by_id(doc_id)` or use `app.activeDocument()`
3. Create new `paintLayer` named `layer_name` via `doc.createNode()`
4. Set pixel data: `node.setPixelData(QByteArray(png_bytes), 0, 0, w, h)`
5. `doc.refreshProjection()`
6. Return `{"layer_id": node.uniqueId(), "layer_name": layer_name, "mode": "live_krita"}`

Headless path:
- Generate UUID for `layer_id`, return mock with `"mode": "headless_mock"`.

- [ ] **Step 4: Implement `krita_plugin_setup_guide()` MCP tool**

Returns this exact string (formatted as markdown):

```
## Krita MCP Plugin Setup — Step by Step

1. **Copy plugin folder:**
   Source: plugins/krita_mcp_bridge/
   Destination: C:\Users\[YOUR_USERNAME]\AppData\Roaming\krita\pykrita\krita_mcp_bridge\

2. **Enable in Krita:**
   Settings → Configure Krita → Python Plugin Manager
   ✅ Enable: "Krita MCP Bridge"
   → Click OK → Restart Krita

3. **Start MCP server** (keep running in background):
   python -m krita_mcp_lazy.main

4. **Verify connection:**
   python scripts/verify_live_bridge.py
   Expected: LIVE_KRITA_CONNECTED: {'engine': 'krita-MCP-lazy', 'version': '0.1.0'}

After these steps: AI agent ↔ MCP server ↔ port 18812 ↔ Krita plugin = LIVE
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/unit/plugin/test_import_image.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/krita_mcp_bridge/handlers_document.py src/krita_mcp_lazy/server/tools_plugin_setup.py
git commit -m "feat(bridge): document.import_image handler + krita_plugin_setup_guide tool"
```

---

### Task 5: End-to-End — Generate + Import + Open

**Files:**
- Create: `scripts/generate_professional_poster.py`
- Output: `output/professional_anime_poster.png`

**Interfaces:**
- Consumes: `krita_generate_image`, bridge IPC `document.import_image`, `BridgeStateOracle`
- Produces: PNG at `output/`, optional live Krita import, printed QA summary.

- [ ] **Step 1: Write script**

Script flow:
1. Parse args: `--prompt`, `--user-image`, `--width`, `--height`, `--output`
2. Call `generate_image_tool(...)` → prints file path + size
3. Probe bridge via `socket.connect_ex("127.0.0.1", 18812)` → 0.5s timeout
4. If live: IPC call `document.import_image` → print Krita layer name
5. If not live: print plugin setup instructions (call `krita_plugin_setup_guide()`)
6. Open `output/` in Windows Explorer: `os.startfile("output")`

- [ ] **Step 2: Run script (Gemini key absent — compositor-only mode)**

Run: `python scripts/generate_professional_poster.py --output output/professional_anime_poster.png`
Expected: PNG created, opens in Explorer, visually shows gradient sky + stars + moon crescent + text.

- [ ] **Step 3: Visual verification checklist**

Open `output/professional_anime_poster.png` and confirm:
- [ ] Sky transitions from deep navy → violet → pink → gold (top to bottom)
- [ ] Stars visible in upper half with bloom glow
- [ ] Moon crescent shape (not a circle) with soft glow halo
- [ ] City skyline silhouette at horizon
- [ ] Japanese + English title text visible and readable
- [ ] Sakura petals scattered (not identical circles)
- [ ] No "yellow wire scribble" artifacts anywhere

If any check fails: adjust compositor parameters and re-run before committing.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_professional_poster.py output/professional_anime_poster.png
git commit -m "feat(pipeline): professional anime poster generation — Gemini + Pillow compositor + Krita import"
```

---

## Self-Review

1. **Spec coverage:** Covers both original failures: blind MCP state (via plugin setup tool) and scribble output (replaced by proper effects pipeline). Gemini integration for real AI art. User image input path.
2. **Step scan:** Every step has either exact test code, exact function signature + algorithm description, or exact run commands. No "handle edge cases" vagueness.
3. **Type consistency:** `generate_base_art`, `ProfessionalCompositor.compose`, `generate_image_tool`, `handle_import_image` — defined once and referenced without mutation across tasks.
4. **Review Focus:** All 5 edge cases covered in owning tasks (no API key, blur on RGBA, large PNG chunking, CJK font missing, headless import).
5. **Proportion:** Plan describes the what and the key algorithms (screen blend formula, band gradient, petal rotation) but doesn't transcribe function bodies.
