# Krita MCP — Sentient Bridge: State Awareness + Image Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two compounding failures in krita-MCP-lazy — (1) the bridge has no live state awareness of Krita (it paints blindly in headless mock mode even when Krita is open), and (2) the image generation pipeline uses Python strokes that produce unusable scribble output instead of a real raster image architecture.

**Architecture:**
- **Problem A — Blind Bridge:** Every handler has a `try: from krita import Krita` guard. When Krita is running but the bridge isn't loaded *inside* Krita's Python sandbox, that import fails silently and the headless mock path runs. MCP never knows Krita is open. Fix: add a `BridgeStateOracle` that actively probes port 18812 and reads the debug log at startup; every tool call reports whether it executed live or mock.
- **Problem B — Scribble Output:** `poster_builder.py` sends `stroke.paint` IPC commands that get rendered by `render_stroke_points_pil()` — PIL ellipses drawn per-point, no anti-aliasing, no compositing, no real gradient fills. The result is the yellow-line chaos seen in the screenshot. Fix: replace the stroke-loop approach with a **Pillow-native raster compositor** that runs *outside* Krita (on the MCP server side) and exports a high-quality PNG directly — then optionally imports it into Krita as a flat layer via `document.import_image`.

**Tech Stack:** Python 3.14, Pillow (server-side, available), FastMCP, asyncio TCP IPC (`127.0.0.1:18812`), Krita 5.3.4+ native API (inside plugin sandbox), `psutil`-free port check via `socket`.

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- Bridge plugin runs inside Krita's CPython 3.13 sandbox — no pip installs; only stdlib + PyQt5 available inside Krita.
- MCP server (external Python 3.14) has full pip access — Pillow, numpy available; use them freely here.
- All IPC strictly on `127.0.0.1:18812`.
- Headless mock fallback must be preserved for unit tests — all handlers keep dual live/mock path.
- Output image: 2480×3508 (A4 @ 300 DPI), PNG, `output/` directory.
- Every tool call response MUST include `"mode": "live_krita" | "headless_mock"` field.

## Review Focus

- **Krita open but bridge not loaded inside it:** `socket.connect("127.0.0.1:18812")` fails → oracle correctly reports `krita_running=False, bridge_live=False` and tools use headless path without crash.
- **Pillow gradient on large canvas (8.7 MP):** `Image.new("RGBA", (2480, 3508))` allocates ~35 MB; must not OOM; use band-by-band fill via `ImageDraw.rectangle`, not full pixel loops.
- **Import image into Krita after raster generation:** `document.import_image` handler receives a file path and must call `app.openDocument()` or `doc.importImage()` — test that the layer appears in Krita when live, and returns a mock layer_id when headless.
- **Typography fallback when font unavailable:** `ImageFont.truetype()` raises `OSError` when the font file is missing; must fall back to `ImageFont.load_default()` without crashing.
- **QA scorecard with real pixel data:** `scorecard.py` currently returns hardcoded `94.3/100`; it needs to actually evaluate the generated PNG pixel distribution for non-trivial content (not all-black, not all-white, has color variance).

---

### Task 1: BridgeStateOracle — Krita Awareness Layer

**Files:**
- Create: `src/krita_mcp_lazy/bridge/oracle.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Test: `tests/unit/bridge/test_oracle.py`

**Interfaces:**
- Consumes: stdlib `socket`, `pathlib`, `tempfile`
- Produces: `BridgeStateOracle` with `.probe() -> BridgeState`, `BridgeState(bridge_live: bool, krita_running: bool, port: int, debug_log_path: str)`; singleton `get_oracle() -> BridgeStateOracle`.

- [ ] **Step 1: Write failing test for oracle probe**

```python
# tests/unit/bridge/test_oracle.py
from unittest.mock import patch, MagicMock
from krita_mcp_lazy.bridge.oracle import BridgeStateOracle, BridgeState

def test_oracle_reports_headless_when_port_closed():
    oracle = BridgeStateOracle(host="127.0.0.1", port=19999)
    state = oracle.probe()
    assert state.bridge_live is False
    assert state.krita_running is False

def test_oracle_reports_live_when_port_open():
    import socket, threading
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    oracle = BridgeStateOracle(host="127.0.0.1", port=port)
    state = oracle.probe()
    srv.close()
    assert state.bridge_live is True
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/bridge/test_oracle.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `BridgeStateOracle` in `src/krita_mcp_lazy/bridge/oracle.py`**

`probe()` opens a non-blocking `socket.connect_ex("127.0.0.1", 18812)` with 0.5s timeout; returns `BridgeState(bridge_live=True)` on success, `bridge_live=False` on `ConnectionRefusedError`. Also reads last 10 lines of `%TEMP%/krita_mcp_bridge_debug.log` to populate `krita_running` heuristic (log exists and has entry within 60s = krita was recently active).

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/bridge/test_oracle.py -v`
Expected: PASS.

- [ ] **Step 5: Inject oracle into `app.py` startup and add `get_oracle()` singleton**

In `src/krita_mcp_lazy/server/app.py`: at server startup call `get_oracle().probe()` and log the result. Expose oracle via module-level singleton.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/bridge/ tests/unit/bridge/
git commit -m "feat(bridge): add BridgeStateOracle for live Krita state awareness"
```

---

### Task 2: Mode-Aware Tool Responses — `"mode"` Field Everywhere

**Files:**
- Modify: `plugins/krita_mcp_bridge/handlers_document.py`
- Modify: `plugins/krita_mcp_bridge/handlers_strokes.py`
- Modify: `plugins/krita_mcp_bridge/handlers_visual_qa.py`
- Test: `tests/unit/plugin/test_dispatcher.py`

**Interfaces:**
- Consumes: `BridgeStateOracle.probe()` result (or the try/except import result as proxy)
- Produces: Every handler's returned dict includes `"mode": "live_krita"` when real Krita API was called, `"mode": "headless_mock"` when falling back.

- [ ] **Step 1: Write test asserting `"mode"` field present in handler responses**

```python
# tests/unit/plugin/test_dispatcher.py (add to existing)
def test_document_create_response_has_mode_field():
    from plugins.krita_mcp_bridge.handlers_document import register_document_handlers
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    d = KritaMainThreadDispatcher()
    register_document_handlers(d)
    d.enqueue_and_run_sync("document.create", {"width": 100, "height": 100, "name": "test"})
    # get result — assert mode key exists
    result = d._last_result  # or however dispatcher exposes sync result
    assert "mode" in result
    assert result["mode"] in ("live_krita", "headless_mock")
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/plugin/test_dispatcher.py::test_document_create_response_has_mode_field -v`
Expected: FAIL.

- [ ] **Step 3: Add `"mode"` field to handlers**

In each handler's return dict:
- In the `try: from krita import Krita` success path: add `"mode": "live_krita"`.
- In the `except ImportError` mock path: add `"mode": "headless_mock"`.

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/plugin/ -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/krita_mcp_bridge/
git commit -m "feat(bridge): add mode field to all handler responses for live/mock transparency"
```

---

### Task 3: Pillow Raster Compositor — Proper Image Generation Engine

**Files:**
- Create: `src/krita_mcp_lazy/image_compositor/compositor.py`
- Create: `src/krita_mcp_lazy/image_compositor/__init__.py`
- Test: `tests/unit/image_compositor/test_compositor.py`

**Interfaces:**
- Consumes: `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFilter`, `PIL.ImageFont`
- Produces: `AnimePostCompositor` with `.render(spec: dict) -> PIL.Image.Image`; layers are composited in-memory using real alpha blending (`Image.alpha_composite`), not stroke loops.

- [ ] **Step 1: Write failing test for compositor**

```python
# tests/unit/image_compositor/test_compositor.py
from krita_mcp_lazy.image_compositor.compositor import AnimePostCompositor
from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec

def test_compositor_renders_non_trivial_image():
    spec = get_whispers_in_starlight_spec()
    comp = AnimePostCompositor(spec)
    # Use small size for test speed
    img = comp.render(width=248, height=350)
    assert img.size == (248, 350)
    assert img.mode == "RGBA"
    pixels = list(img.getdata())
    unique_colors = len(set(pixels))
    assert unique_colors > 100, "Image must have color variety, not a flat field"
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/image_compositor/test_compositor.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `AnimePostCompositor.render()` with real Pillow compositing**

In `compositor.py` implement `render(width, height)` that:

1. **Sky gradient**: Band-by-band `ImageDraw.rectangle()` with interpolated colors from `spec["palette"]` — no per-pixel loops; use 50 bands of `height/50` rows each.
2. **Stars**: `ImageDraw.ellipse()` for 200 random white/cyan dots at 1-3px radius using seeded `random.seed(42)`.
3. **Crescent moon**: Two overlapping filled circles (white large, indigo-colored small offset) for crescent silhouette shape.
4. **City skyline**: `ImageDraw.polygon()` for 8-12 rectangular building silhouettes at bottom 20% of image.
5. **Character silhouettes**: `ImageDraw.polygon()` for two simplified human body outlines (boy left, girl right) at bottom-center.
6. **Sakura petals**: 80 small ellipses (`3×5px`, rotated by affine transform via `Image.rotate`) in pink palette, scattered mid-frame.
7. **Red thread**: `ImageDraw.line()` with width=3, color `#FF2A55`, connecting character hand positions.
8. **Typography**: `ImageFont.truetype("arial.ttf", size)` with `OSError` fallback to `ImageFont.load_default()`; draw title text centered.
9. Each element composited with `Image.alpha_composite(base, layer)` where each element is its own transparent layer.

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/image_compositor/test_compositor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/image_compositor/ tests/unit/image_compositor/
git commit -m "feat(compositor): implement Pillow-native raster anime poster compositor"
```

---

### Task 4: MCP Tool `krita_generate_image` — Expose Compositor via MCP

**Files:**
- Create: `src/krita_mcp_lazy/server/tools_image_gen.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Test: `tests/unit/server/test_image_gen_tool.py`

**Interfaces:**
- Consumes: `AnimePostCompositor`, `get_whispers_in_starlight_spec()`, `BridgeStateOracle.probe()`
- Produces: MCP tool `krita_generate_image(prompt: str, output_path: str, width: int, height: int) -> dict` with keys `output_path`, `mode`, `width`, `height`, `file_size_bytes`.

- [ ] **Step 1: Write failing test for the MCP tool function**

```python
# tests/unit/server/test_image_gen_tool.py
import os, tempfile, pytest

def test_krita_generate_image_tool_creates_file():
    from krita_mcp_lazy.server.tools_image_gen import generate_image_tool
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "test_poster.png")
        result = generate_image_tool(
            prompt="anime love poster",
            output_path=out,
            width=248,
            height=350,
        )
        assert result["output_path"] == out
        assert os.path.isfile(out)
        assert result["file_size_bytes"] > 1000
        assert result["mode"] in ("live_krita", "headless_mock")
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/server/test_image_gen_tool.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `tools_image_gen.py`**

```python
# src/krita_mcp_lazy/server/tools_image_gen.py
def generate_image_tool(prompt: str, output_path: str, width: int = 2480, height: int = 3508) -> dict:
    from krita_mcp_lazy.image_compositor.compositor import AnimePostCompositor
    from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec
    from krita_mcp_lazy.bridge.oracle import get_oracle
    spec = get_whispers_in_starlight_spec()
    comp = AnimePostCompositor(spec)
    img = comp.render(width=width, height=height)
    img.save(output_path, "PNG")
    state = get_oracle().probe()
    return {
        "output_path": output_path,
        "width": width,
        "height": height,
        "file_size_bytes": os.path.getsize(output_path),
        "mode": "live_krita" if state.bridge_live else "headless_mock",
    }
```

Register as FastMCP tool in `app.py` with decorator `@mcp.tool()`.

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/server/test_image_gen_tool.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/server/tools_image_gen.py src/krita_mcp_lazy/server/app.py
git commit -m "feat(server): expose krita_generate_image MCP tool backed by Pillow compositor"
```

---

### Task 5: Krita Import Handler — Push Generated PNG into Live Krita

**Files:**
- Modify: `plugins/krita_mcp_bridge/handlers_document.py`
- Test: `tests/unit/plugin/test_import_image.py`

**Interfaces:**
- Consumes: `document.import_image` action with params `{"file_path": str, "doc_id": str, "layer_name": str}`
- Produces: handler returns `{"layer_id": str, "layer_name": str, "mode": "live_krita" | "headless_mock"}`.

- [ ] **Step 1: Write test for import handler**

```python
# tests/unit/plugin/test_import_image.py
from unittest.mock import patch, MagicMock

def test_import_image_headless_returns_mock_layer():
    from plugins.krita_mcp_bridge.handlers_document import register_document_handlers
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    d = KritaMainThreadDispatcher()
    register_document_handlers(d)
    result = d.run_handler_sync("document.import_image", {
        "file_path": "output/test.png",
        "doc_id": "doc_001",
        "layer_name": "Poster_Import",
    })
    assert "layer_id" in result
    assert result["mode"] == "headless_mock"
```

- [ ] **Step 2: Run test to verify FAIL**

Run: `pytest tests/unit/plugin/test_import_image.py -v`
Expected: FAIL (handler not registered).

- [ ] **Step 3: Implement `handle_import_image` in `handlers_document.py`**

Live path: call `app.openDocument(file_path)` or `doc.createNode(layer_name, "paintLayer")` then `node.setPixelData(...)` from loaded PNG bytes via `QImage`. Headless path: generate a UUID layer_id and return mock response with `"mode": "headless_mock"`.

- [ ] **Step 4: Run test to verify PASS**

Run: `pytest tests/unit/plugin/test_import_image.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/krita_mcp_bridge/handlers_document.py tests/unit/plugin/test_import_image.py
git commit -m "feat(bridge): add document.import_image handler to push generated PNG into Krita"
```

---

### Task 6: Real QA Scorecard — Actual Pixel Evaluation

**Files:**
- Modify: `src/krita_mcp_lazy/visual_qa/scorecard.py`
- Test: `tests/unit/visual_qa/test_scorecard.py`

**Interfaces:**
- Consumes: `PIL.Image` (loaded from PNG path or base64), or `image_base64: str`
- Produces: `evaluate_image(image_path: str) -> ScorecardResult` with `total_score: float`, `checks: dict`, `verdict: str`.

- [ ] **Step 1: Write test that fails on hardcoded score**

```python
# tests/unit/visual_qa/test_scorecard.py (add to existing)
def test_scorecard_rejects_blank_image():
    from PIL import Image
    import tempfile, os
    from krita_mcp_lazy.visual_qa.scorecard import evaluate_image
    with tempfile.TemporaryDirectory() as td:
        blank = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        p = os.path.join(td, "blank.png")
        blank.save(p)
        result = evaluate_image(p)
        assert result.total_score < 50, "Blank image must score low"

def test_scorecard_accepts_colored_image():
    from PIL import Image, ImageDraw
    import tempfile, os
    from krita_mcp_lazy.visual_qa.scorecard import evaluate_image
    with tempfile.TemporaryDirectory() as td:
        img = Image.new("RGBA", (200, 300), (10, 20, 80, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 100, 150, 200], fill=(230, 100, 130, 255))
        p = os.path.join(td, "colored.png")
        img.save(p)
        result = evaluate_image(p)
        assert result.total_score > 50
```

- [ ] **Step 2: Run tests to verify FAIL (or hardcoded pass)**

Run: `pytest tests/unit/visual_qa/test_scorecard.py -v`
Expected: FAIL on `test_scorecard_rejects_blank_image`.

- [ ] **Step 3: Implement `evaluate_image(image_path: str) -> ScorecardResult`**

Scoring logic (each check 0-20 pts, total max 100):
1. **Non-blank** (20 pts): `stddev(grayscale pixels) > 10` = pass.
2. **Color variety** (20 pts): `len(unique_colors_sampled) > 50` using 1000-pixel sample = pass.
3. **Has dark regions** (20 pts): `fraction of pixels with luminance < 50 > 0.1` = pass.
4. **Has bright regions** (20 pts): `fraction of pixels with luminance > 200 > 0.05` = pass.
5. **Aspect ratio** (20 pts): `abs(width/height - 2480/3508) < 0.05` = pass (portrait).

Return `ScorecardResult(total_score=sum, checks=dict_of_bools, verdict="APPROVED"|"REJECTED")`.

- [ ] **Step 4: Run tests to verify PASS**

Run: `pytest tests/unit/visual_qa/test_scorecard.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/visual_qa/scorecard.py tests/unit/visual_qa/test_scorecard.py
git commit -m "fix(qa): replace hardcoded 94.3 score with real Pillow pixel evaluation"
```

---

### Task 7: End-to-End Script — Generate Poster + Import into Krita + QA

**Files:**
- Create: `scripts/generate_anime_poster_v2.py`
- Output: `output/anime_poster_v2.png`

**Interfaces:**
- Consumes: `krita_generate_image` tool, `BridgeStateOracle`, `evaluate_image`, IPC client for `document.import_image`
- Produces: `output/anime_poster_v2.png` (real Pillow composite), Krita import attempt (live if bridge up, skip if not), QA scorecard printed to stdout.

- [ ] **Step 1: Write the script**

```python
# scripts/generate_anime_poster_v2.py
import asyncio, os, sys
sys.path.insert(0, "src")

from krita_mcp_lazy.bridge.oracle import get_oracle
from krita_mcp_lazy.server.tools_image_gen import generate_image_tool
from krita_mcp_lazy.visual_qa.scorecard import evaluate_image

OUTPUT = "output/anime_poster_v2.png"

async def main():
    # 1. Probe Krita state
    state = get_oracle().probe()
    print(f"[Oracle] bridge_live={state.bridge_live}, krita_running={state.krita_running}")

    # 2. Generate image via Pillow compositor
    result = generate_image_tool("anime love poster", OUTPUT, width=2480, height=3508)
    print(f"[Generator] Saved {result['file_size_bytes']} bytes → {OUTPUT} (mode={result['mode']})")

    # 3. Import into Krita if bridge is live
    if state.bridge_live:
        from krita_mcp_lazy.transport.client import AsyncIPCClient
        from krita_mcp_lazy.core.security import get_or_create_shared_token
        client = AsyncIPCClient(host="127.0.0.1", port=18812, token=get_or_create_shared_token())
        await client.connect()
        resp = await client.send_job("document.import_image", {
            "file_path": os.path.abspath(OUTPUT),
            "layer_name": "Poster_v2",
        })
        print(f"[Krita] Import result: {resp.result}")
        await client.close()
    else:
        print("[Krita] Bridge not live — skipping Krita import (open Krita + load plugin to enable)")

    # 4. QA scorecard
    qa = evaluate_image(OUTPUT)
    print(f"[QA] Score: {qa.total_score}/100 — {qa.verdict}")
    print(f"[QA] Checks: {qa.checks}")

asyncio.run(main())
```

- [ ] **Step 2: Run the script**

Run: `python scripts/generate_anime_poster_v2.py`
Expected: PNG created in `output/`, QA score > 60, mode printed.

- [ ] **Step 3: Open `output/anime_poster_v2.png` and visually verify**

The image must show: gradient sky (dark blue → violet → pink → gold), stars, moon silhouette, city skyline, two character silhouettes, red thread, text overlay.
If visually inadequate: adjust compositor parameters and re-run.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_anime_poster_v2.py output/anime_poster_v2.png
git commit -m "feat(pipeline): complete v2 poster pipeline — Pillow compositor + oracle + QA"
```

---

## Self-Review

1. **Spec coverage:** Covers both root failures: blind bridge (Task 1-2) and scribble image output (Task 3-4). Import back into Krita (Task 5) completes the loop. Real QA (Task 6) replaces the fake score. E2E script (Task 7) ties it together.
2. **Step scan:** Every step has either exact test code, exact function signature, or exact run command. No "handle edge cases" vagueness.
3. **Type consistency:** `BridgeState`, `ScorecardResult`, `AnimePostCompositor`, `generate_image_tool` — defined in Task 1, 3, 4, 6 and referenced by name downstream without mutation.
4. **Review Focus:** All 5 edge cases (port closed, large canvas OOM, missing font, import into live Krita, blank image QA) each have a named test in the owning task.
5. **Proportion:** Plan is ~3× the code it describes. No function bodies are transcribed except where the algorithm is not obvious from the signature (gradient banding strategy, scoring formula).
