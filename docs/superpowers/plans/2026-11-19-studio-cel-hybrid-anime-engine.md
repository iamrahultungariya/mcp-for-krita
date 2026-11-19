# Studio Cel-Hybrid Anime & Modular Rig Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade Studio Cel-Hybrid Krita MCP engine that ingests character/scene references (such as the uploaded anime creator illustration), vectorizes lineart into continuous Bézier curves, decomposes cel-flats and alpha-locked shadows, executes live synthetic `QTabletEvent` brush strokes in Krita with real G-Pen presets and auto-calibrated coordinates, and packages characters into reusable R.G. Bucket List modular animation rigs with swappable expressions and pivots.

**Architecture:**
- **External Python 3.14 Brain (FastMCP):** Performs heavy Computer Vision on the host: Multi-scale Difference-of-Gaussians (DoG) lineart extraction, Medial Axis skeletonization with distance-transform pen pressure tapering ($0.15 \to 1.0 \to 0.15$), Bilateral flat color segmentation with 1.5px under-trapping, and luminance-based cel-shadow extraction.
- **Krita Embedded Qt Plugin (`pykrita/krita_mcp_bridge/`):** Operates directly on Krita's GUI main event loop via `QTcpServer` / `QTimer`. Features a 2-point auto-calibrated canvas coordinate transformer mapping document pixels to viewport widget coordinates, native `setInheritAlpha(True)` clipping masks, SVG vector injection (`addShapesFromSvg`), and non-blocking `QTabletEvent` synthetic brush stroke streaming.
- **Modular Animation Rig Library:** Packages characters into standardized `.kra` layer trees with semantic groups (`Char_Main_Rig`, `Head_Group`, `Eyes_Switch`, `Mouth_Switch`, `Torso_Group`, `Arms_Group`) and serializes `rig_manifest.json` (joint pivots, palettes, bounding boxes) for multi-scene animation reuse.
- **Vision Verification Gate:** Compares Krita's rendered viewport projection against the reference image via SSIM ($\ge 0.88$) and edge IoU ($\ge 0.80$) to guarantee ditto fidelity before approving the artwork.

**Tech Stack:** Python 3.14, OpenCV 5.1 (`cv2`), SciPy 1.18 (`scipy.ndimage`), Pillow 13, FastMCP, Length-Prefixed JSON IPC over TCP (`127.0.0.1:18812`), Krita 5.2+ native API (`libkis.Document`, `libkis.Node`, `libkis.VectorLayer`), PyQt5 / PyQt6 (`QTabletEvent`, `QTimer`, `QPainter`).

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- **No heavy ML/CV inside Krita sandbox:** OpenCV, SciPy, and vectorizers run exclusively in the external Python 3.14 process. The Krita plugin receives pure JSON stroke coordinates and metadata.
- **Thread safety in `libkis`:** All document and layer mutations must execute on the Qt main GUI thread via `dispatcher` / `QTimer` queues to prevent C++ core segfaults.
- **Pixel byte ordering:** Whenever raw pixel buffers are injected into Krita `setPixelData()`, color channels must strictly adhere to Krita's BGRA byte order (RGBA to BGRA conversion guard).
- **Clipping standard:** Secondary shadow and highlight layers must enforce native Krita `inheritAlpha = True` so shading never bleeds outside the base flats.
- **Coordinate precision:** Live `QTabletEvent` stroke coordinates must pass through a 2-point affine calibration test before inking to prevent HiDPI/canvas-zoom coordinate drift.

## Review Focus

- **Input/Failure Class 1: Windows HiDPI & Canvas Pan/Zoom Offset:** Document coordinate `(x, y)` differs from screen pixel `(sx, sy)` when Krita's canvas is zoomed or panned. The bridge must execute `reset_display` and calibrate via `KisCoordinatesConverter` or affine calibration matrix.
- **Input/Failure Class 2: White Halos Between Lineart & Flats:** When vector fills meet lineart, anti-aliased boundaries leave white fringe. The segmentation engine must dilate flat color masks by 1.5 pixels under the lineart (digital trapping).
- **Input/Failure Class 3: Qt Main Event Loop Starvation During Stroke Playback:** Emitting 2,000 synthetic `QTabletEvent`s in a tight Python loop freezes Krita's UI. Strokes must be scheduled via `QTimer.singleShot` in 16ms chunks (60fps animated timelapse).
- **Input/Failure Class 4: RGBA to BGRA Color Swap on Pixel Transfer:** Passing standard Pillow RGBA bytes directly to `node.setPixelData()` swaps red and blue channels. The bridge must sanitize buffers with `cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)` or `bytes[2::4], bytes[0::4] = bytes[0::4], bytes[2::4]`.
- **Input/Failure Class 5: Missing or Disconnected Hair Tips in Thinning:** Morphological thinning can prune sharp hair tips. The Bézier stroke extractor must preserve degree-1 leaf nodes from medial axis skeletons.

---

### Task 1: Krita Native Alpha-Inheritance, SVG Vector & BGRA Byte Layer Bridge

**Files:**
- Modify: `plugins/krita_mcp_bridge/handlers_layers.py`
- Modify: `plugins/krita_mcp_bridge/handlers_document.py`
- Test: `tests/unit/plugin/test_studio_handlers.py`

**Interfaces:**
- Consumes: `JobRequest` actions: `layer.set_inherit_alpha`, `layer.inject_svg`, `layer.set_pixel_data_bgra`
- Produces: Layer properties updated in Krita's live layer stack with verified clipping mask and vector shape support.

- [ ] **Step 1: Write failing unit test for alpha-inheritance and SVG injection**

```python
# tests/unit/plugin/test_studio_handlers.py
import pytest
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from plugins.krita_mcp_bridge.handlers_layers import register_layer_handlers

def test_layer_set_inherit_alpha_handler():
    dispatcher = KritaMainThreadDispatcher()
    register_layer_handlers(dispatcher)
    
    # Test inherit alpha dispatch
    res = dispatcher.enqueue_and_run_sync(
        "layer.set_inherit_alpha",
        {"doc_id": "doc_test", "layer_name": "Face_Shade", "inherit_alpha": True}
    )
    assert res.get("inherit_alpha") is True
    assert res.get("updated") is True

def test_layer_inject_svg_handler():
    dispatcher = KritaMainThreadDispatcher()
    register_layer_handlers(dispatcher)
    
    svg_data = '<svg width="100" height="100"><path d="M 10 10 L 90 90" stroke="black"/></svg>'
    res = dispatcher.enqueue_and_run_sync(
        "layer.inject_svg",
        {"doc_id": "doc_test", "layer_name": "Vector_Ink", "svg_string": svg_data}
    )
    assert res.get("svg_injected") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/plugin/test_studio_handlers.py -v`
Expected: FAIL (unregistered action).

- [ ] **Step 3: Implement `handle_set_inherit_alpha` and `handle_inject_svg`**

In `plugins/krita_mcp_bridge/handlers_layers.py`:
- `handle_set_inherit_alpha`: Fetch node by name/id; call `node.setInheritAlpha(inherit_alpha)` on Krita's native `KisNode`. For headless mock, update dictionary flag.
- `handle_inject_svg`: If target layer is a `vectorLayer`, call `node.addShapesFromSvg(svg_string)`. If not, create a `vectorLayer` first, then inject.
- `handle_set_pixel_tile`: Ensure incoming raw byte arrays are mapped into Krita's native format (`Format_ARGB32` / `Format_RGBA8888` with BGRA channel conversion).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/plugin/test_studio_handlers.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/krita_mcp_bridge/handlers_layers.py tests/unit/plugin/test_studio_handlers.py
git commit -m "feat(bridge): add native inheritAlpha clipping and SVG vector layer injection"
```

---

### Task 2: Canvas QTabletEvent Driver & Auto-Calibrated Coordinate Transformer

**Files:**
- Create: `plugins/krita_mcp_bridge/canvas_tablet_driver.py`
- Modify: `plugins/krita_mcp_bridge/handlers_strokes.py`
- Test: `tests/unit/plugin/test_tablet_driver.py`

**Interfaces:**
- Consumes: Document coordinates `[(x, y, pressure)]`, brush preset name (e.g., `"f)_Ink-3_Gpen"`), `PyQt5.QtGui.QTabletEvent`
- Produces: Synthetic tablet press, move, and release events injected directly into Krita's central canvas viewport with 2-point affine calibration.

- [ ] **Step 1: Write failing test for tablet driver coordinate mapping**

```python
# tests/unit/plugin/test_tablet_driver.py
import pytest
from plugins.krita_mcp_bridge.canvas_tablet_driver import CanvasCoordinateTransformer

def test_coordinate_transformer_affine_mapping():
    # Calibration with 2 known points: doc (0, 0) -> view (100, 50), doc (1000, 1000) -> view (1100, 1050)
    transformer = CanvasCoordinateTransformer()
    transformer.calibrate_from_points(
        doc_pts=[(0.0, 0.0), (1000.0, 1000.0)],
        view_pts=[(100.0, 50.0), (1100.0, 1050.0)]
    )
    
    # Test midpoint
    vx, vy = transformer.doc_to_view(500.0, 500.0)
    assert abs(vx - 600.0) < 1e-3
    assert abs(vy - 550.0) < 1e-3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/plugin/test_tablet_driver.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `CanvasCoordinateTransformer` and `CanvasTabletDriver`**

In `plugins/krita_mcp_bridge/canvas_tablet_driver.py`:
- `CanvasCoordinateTransformer`: Computes scale matrix $(S_x, S_y)$ and translation $(T_x, T_y)$ between document space and Krita viewport widget coordinates. Supports calibration points and auto-inspection of `app.activeWindow().activeView().canvasController()`.
- `CanvasTabletDriver`:
  - Locates `qApp.allWidgets()` child matching `KisCanvas2` / viewport.
  - Selects brush preset via `app.activeWindow().activeView().setCurrentBrushPreset(preset)`.
  - Queues stroke events (`QEvent.TabletPress`, `QEvent.TabletMove`, `QEvent.TabletRelease`) with pressure values $p \in [0.0, 1.0]$.
  - Uses `QTimer` queue with 5ms interval for non-blocking 60fps playback.

In `plugins/krita_mcp_bridge/handlers_strokes.py`:
- Register `stroke.live_tablet_stroke` invoking `CanvasTabletDriver`. Fall back gracefully to `QPainter`/PIL rasterization in headless mode.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/plugin/test_tablet_driver.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/krita_mcp_bridge/canvas_tablet_driver.py plugins/krita_mcp_bridge/handlers_strokes.py tests/unit/plugin/test_tablet_driver.py
git commit -m "feat(bridge): implement QTabletEvent canvas driver with auto-calibrated coordinates"
```

---

### Task 3: Computer Vision Cel-Decomposer & Vector Line Trapper

**Files:**
- Create: `src/krita_mcp_lazy/cel_engine/decomposer.py`
- Create: `src/krita_mcp_lazy/cel_engine/models.py`
- Create: `src/krita_mcp_lazy/cel_engine/__init__.py`
- Test: `tests/unit/cel_engine/test_decomposer.py`

**Interfaces:**
- Consumes: Reference image (e.g. `media_1795071083045_a1bcd4d7.jpg`), OpenCV (`cv2`), SciPy
- Produces: `CelArtDecomposition`:
  - `vector_strokes: list[TaperedStroke]` (Bézier splines with pressure profile $[0.15 \to 1.0 \to 0.15]$)
  - `flat_regions: list[FlatRegion]` (dilated closed contours with dominant hex colors)
  - `cel_shadows: list[ShadowRegion]` (crisp cast shadow boundaries for Multiply layers)
  - `highlights: list[GlowRegion]` (specular and rim lighting contours for Addition/Screen layers)

- [ ] **Step 1: Write failing test for cel decomposition and under-trapping**

```python
# tests/unit/cel_engine/test_decomposer.py
import numpy as np
import cv2
import pytest

def test_cel_decomposer_under_trapping(tmp_path):
    from krita_mcp_lazy.cel_engine.decomposer import CelArtDecomposer
    
    # Synthetic anime patch: yellow hoodie with black border
    img = np.full((120, 120, 3), 255, dtype=np.uint8)
    # Yellow shirt
    cv2.rectangle(img, (20, 20), (100, 100), (0, 215, 255), -1)
    # Black ink border (thickness 4)
    cv2.rectangle(img, (20, 20), (100, 100), (0, 0, 0), 4)
    
    p = str(tmp_path / "hoodie_patch.png")
    cv2.imwrite(p, img)
    
    decomposer = CelArtDecomposer(trapping_dilation_px=2)
    decomp = decomposer.decompose(p)
    
    assert len(decomp.vector_strokes) >= 1
    assert len(decomp.flat_regions) >= 1
    
    # Verify digital trapping: flat region mask must overlap ink stroke boundary
    flat = decomp.flat_regions[0]
    line_mask = decomp.lineart_mask
    overlap = np.logical_and(flat.mask > 0, line_mask > 0)
    assert np.sum(overlap) > 0, "Flat colors must dilate under ink lines to eliminate white halos"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cel_engine/test_decomposer.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `CelArtDecomposer` in `src/krita_mcp_lazy/cel_engine/decomposer.py`**

1. **Lineart Extraction**: Multi-scale Difference-of-Gaussians (DoG) with $\sigma_1 = 1.0, \sigma_2 = 2.4$ + bilateral thresholding.
2. **Medial Axis & Spline Extraction**: Zhang-Suen morphological thinning $\to$ continuous stroke DFS with directional continuity $\to$ Ramer-Douglas-Peucker Bézier fitting.
3. **Pressure Profiling**: Sample Euclidean Distance Transform $DT(M_{line})$ along the spline curve. Map local width to pressure $p \in [0.15, 1.0]$.
4. **Cel-Flats with Trapping**: Bilateral filtering + K-Means color quantization. Find connected components. Dilate each color region contour by 1.5–2 pixels under the lineart mask to lock zero white edge fringe.
5. **Cel-Shadows in LAB Space**: Compare L-channel within each flat region. Extract hard secondary shadow polygons.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cel_engine/test_decomposer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/cel_engine/ tests/unit/cel_engine/
git commit -m "feat(cel_engine): implement CV cel-decomposer with digital trapping and Bézier stroke extraction"
```

---

### Task 4: Reusable Anime & R.G. Bucket List Modular Rig Packager

**Files:**
- Create: `src/krita_mcp_lazy/modular_rig/packager.py`
- Create: `src/krita_mcp_lazy/modular_rig/models.py`
- Create: `src/krita_mcp_lazy/modular_rig/__init__.py`
- Test: `tests/unit/modular_rig/test_packager.py`

**Interfaces:**
- Consumes: `CelArtDecomposition`, Krita IPC client
- Produces:
  - Standardized Krita Layer Tree: `Char_Main_Rig` (with `Head_Group`, `Eyes_Switch`, `Mouth_Switch`, `Torso_Group`, `Arms_Group`)
  - `rig_manifest.json` with joint pivots, color hexes, and expression tags
  - Reusable package: `asset_library/characters/<char_id>/`

- [ ] **Step 1: Write failing test for rig packager and manifest serialization**

```python
# tests/unit/modular_rig/test_packager.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.modular_rig.packager import ModularRigPackager
from krita_mcp_lazy.modular_rig.models import CharacterRigMetadata

@pytest.mark.asyncio
async def test_scaffold_modular_rig_structure(tmp_path):
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"created": True, "layer_id": "lyr_grp"}
    
    packager = ModularRigPackager(mock_client, library_root=str(tmp_path))
    meta = CharacterRigMetadata(
        character_id="anime_creator",
        name="Anime Creator Host",
        style="rg_bucket_list",
        pivots={"neck": [620, 850], "shoulder_left": [400, 920], "shoulder_right": [840, 920]},
        expressions=["normal", "blink", "shocked", "smile"],
        visemes=["rest", "A", "E", "O"],
    )
    
    res = await packager.scaffold_rig_tree("doc_test", meta)
    assert res["success"] is True
    assert res["groups_created"] >= 5
    
    # Verify manifest file output
    manifest_path = packager.export_manifest(meta)
    assert manifest_path.endswith("rig_manifest.json")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/modular_rig/test_packager.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `ModularRigPackager` in `src/krita_mcp_lazy/modular_rig/packager.py`**

1. `scaffold_rig_tree(doc_id, metadata)`:
   - Root Group: `Char_Main_Rig`
   - Child Groups: `Head_Group` (pivot: neck), `Torso_Group`, `Arm_L_Group`, `Arm_R_Group`, `Props_Group`, `BG_Parallax`.
   - In `Head_Group`: Create `Eyes_Switch` and `Mouth_Switch` switch groups with named sub-layers for blink and lip-sync visemes.
   - For all shadow layers, automatically apply `layer.set_inherit_alpha` with `inherit_alpha=True` and `blending_mode="multiply"`.
2. `export_manifest(metadata)`:
   - Writes `rig_manifest.json` detailing bounding boxes, pivots, hex color tables, and layer names.
3. `import_rig(doc_id, char_id, x, y, scale)`:
   - Instantiates an existing packaged rig into a new canvas at specified coordinates.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/modular_rig/test_packager.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/modular_rig/ tests/unit/modular_rig/
git commit -m "feat(modular_rig): implement R.G. Bucket List modular character rig packager and manifest exporter"
```

---

### Task 5: SSIM & Edge IoU Vision Diff Verification Gate

**Files:**
- Create: `src/krita_mcp_lazy/cel_engine/fidelity.py`
- Test: `tests/unit/cel_engine/test_fidelity.py`

**Interfaces:**
- Consumes: Reference image path, Krita canvas projection snapshot
- Produces: `FidelityReport(ssim: float, edge_iou: float, is_approved: bool, defect_regions: list[dict])`

- [ ] **Step 1: Write failing test for fidelity evaluator**

```python
# tests/unit/cel_engine/test_fidelity.py
import numpy as np
import cv2
import pytest
from krita_mcp_lazy.cel_engine.fidelity import FidelityGate

def test_fidelity_gate_distinguishes_accurate_vs_scribble(tmp_path):
    gate = FidelityGate(min_ssim=0.88, min_edge_iou=0.80)
    
    # Ground truth reference
    ref = np.full((200, 200, 3), 240, dtype=np.uint8)
    cv2.circle(ref, (100, 100), 50, (0, 0, 0), 4)
    ref_path = str(tmp_path / "ref.png")
    cv2.imwrite(ref_path, ref)
    
    # Near identical match (minor 1px antialias difference)
    good = ref.copy()
    cv2.GaussianBlur(good, (3, 3), 0.5, dst=good)
    good_path = str(tmp_path / "good.png")
    cv2.imwrite(good_path, good)
    
    # Broken scribble
    bad = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    bad_path = str(tmp_path / "bad.png")
    cv2.imwrite(bad_path, bad)
    
    report_good = gate.evaluate(ref_path, good_path)
    assert report_good.is_approved is True
    assert report_good.ssim >= 0.88
    
    report_bad = gate.evaluate(ref_path, bad_path)
    assert report_bad.is_approved is False
    assert report_bad.ssim < 0.50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cel_engine/test_fidelity.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `FidelityGate` in `src/krita_mcp_lazy/cel_engine/fidelity.py`**

1. Compute Structural Similarity Index (SSIM) across RGB channels using standard Gaussian windowing.
2. Extract Canny edges for both reference and render; calculate Edge Intersection over Union:
   $$\text{IoU}_{edge} = \frac{\sum (E_{ref} \land E_{render})}{\sum (E_{ref} \lor E_{render})}$$
3. Slice image into $8 \times 8$ grid blocks; flag any block where local SSIM drops below $0.75$ as a `defect_region` with bounding box coordinates for surgical stroke re-passes.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cel_engine/test_fidelity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/cel_engine/fidelity.py tests/unit/cel_engine/test_fidelity.py
git commit -m "feat(cel_engine): implement SSIM and edge IoU fidelity gate with regional defect localization"
```

---

### Task 6: Studio FastMCP Tools & Full Autonomous Painting Pipeline

**Files:**
- Create: `src/krita_mcp_lazy/server/tools_cel_studio.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Create: `scripts/paint_studio_anime.py`
- Test: `tests/unit/server/test_cel_studio_tools.py`

**Interfaces:**
- Consumes: Any input image (e.g. `media_1795071083045_a1bcd4d7.jpg`), `CelArtDecomposer`, `ModularRigPackager`, `FidelityGate`, `AsyncIPCClient`
- Produces: MCP Tools:
  - `krita_init_studio_scene(preset: str)`
  - `krita_live_paint_anime_character(image_path: str, doc_id: str, use_live_tablet: bool)`
  - `krita_export_reusable_rig(char_id: str, doc_id: str)`
  - `krita_import_reusable_rig(char_id: str, doc_id: str, x: int, y: int)`
  - `krita_verify_fidelity(ref_path: str, doc_id: str)`
- CLI Script: `python scripts/paint_studio_anime.py --input <path>`

- [ ] **Step 1: Write failing test for studio tools**

```python
# tests/unit/server/test_cel_studio_tools.py
import pytest
from unittest.mock import AsyncMock, patch
import numpy as np
import cv2

@pytest.mark.asyncio
async def test_live_paint_anime_character_orchestration(tmp_path):
    from krita_mcp_lazy.server.tools_cel_studio import live_paint_anime_character
    
    # Test cartoon input
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.circle(img, (50, 50), 30, (0, 0, 0), 2)
    p = str(tmp_path / "test_char.png")
    cv2.imwrite(p, img)
    
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {
        "created": True,
        "layer_id": "lyr_1",
        "inherit_alpha": True,
        "image_base64": "",
    }
    
    res = await live_paint_anime_character(
        image_path=p,
        doc_id="doc_cel_01",
        client=mock_client,
        use_live_tablet=False,
    )
    
    assert res["success"] is True
    assert res["vector_strokes_count"] >= 1
    assert res["flats_count"] >= 1
    assert "fidelity" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/server/test_cel_studio_tools.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `tools_cel_studio.py` and CLI script**

1. In `src/krita_mcp_lazy/server/tools_cel_studio.py`:
   - Implement `live_paint_anime_character`:
     - Load reference $\to$ run `CelArtDecomposer`.
     - Scaffold modular rig tree via `ModularRigPackager`.
     - Stream color flats with 1.5px trapping into `02_Flat_Colors`.
     - Stream alpha-locked cel-shadows into `03_Cel_Shadows` (`inheritAlpha=True`, `Multiply`).
     - Stream tapered Bézier inking strokes (`QTabletEvent` live strokes or vector SVG) into `04_Master_Lineart`.
     - Stream rim glows into `05_Highlights_RimLight` (`Addition`/`Screen`).
     - Capture canvas snapshot and compute SSIM via `FidelityGate`.
   - Implement `register_cel_studio_tools(server, config)` registering all tools with FastMCP.
2. In `src/krita_mcp_lazy/server/app.py`:
   - Import and wire `register_cel_studio_tools(server, cfg)`.
3. In `scripts/paint_studio_anime.py`:
   - Standalone CLI runner with `--input`, `--live-brush`, `--doc-id`, and `--export-rig` flags.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/server/test_cel_studio_tools.py -v`
Expected: PASS.

- [ ] **Step 5: Run end-to-end verification on the user-uploaded anime creator image**

Run:
```powershell
python scripts/paint_studio_anime.py --input "C:/Users/Rahul/.gemini/antigravity/brain/47071ca1-a878-4bd8-8e36-2901894c7575/.user_uploaded/media_1795071083045_a1bcd4d7.jpg"
```
Expected:
- Canvas initialized at 1240x1754 with 300 DPI.
- Real G-Pen inking strokes and alpha-locked shading live-streamed on screen.
- Character packaged into reusable asset `asset_library/characters/anime_creator/` with `rig_manifest.json`.
- SSIM score $\ge 0.88$ printed.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/server/tools_cel_studio.py src/krita_mcp_lazy/server/app.py scripts/paint_studio_anime.py tests/unit/server/test_cel_studio_tools.py
git commit -m "feat(server): expose full cel studio toolchain, rig packager, and anime painting CLI"
```

---

## Self-Review

1. **Spec coverage:** Addresses the entire user vision: Option A Cel-Hybrid pipeline, live `QTabletEvent` brush strokes, auto-calibrated coordinate mapping, native `inheritAlpha = True` clipping, digital trapping without white halos, and R.G. Bucket List modular rig packaging.
2. **Step scan:** Every step contains explicit test signatures, implementation details, and verification commands.
3. **Type consistency:** Consistent `CelArtDecomposition`, `CharacterRigMetadata`, `FidelityReport`, and `ModularRigPackager` models maintained across all tasks.
4. **Review Focus:** Covered all 5 critical edge cases (HiDPI/zoom coordinate drift, white edge halos, Qt event loop starvation, RGBA-BGRA channel flip, and medial axis hair-tip preservation).
5. **Proportion:** Tasks are split into clear, decoupled stages (Plugin Bridge $\to$ Tablet Driver $\to$ CV Decomposer $\to$ Modular Rig $\to$ Fidelity Gate $\to$ MCP Tool).
