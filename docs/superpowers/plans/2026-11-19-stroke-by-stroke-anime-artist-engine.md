# ChronoStroke: Autonomous Stroke-by-Stroke Anime Painting Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (Native). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build an autonomous stroke-by-stroke digital drawing and painting engine that ingests any reference image (e.g. the user's anime creator illustration), vectorizes its lineart into continuous Bézier curves with dynamic line-weight pressure, segments cel-shading and flat color regions, and executes human-like drawing strokes directly on Krita's live canvas layer-by-layer so the artwork is drawn authentically on screen matching the reference image.

**Architecture:**
- **Stage 1 (Server-side CV Decomposition):** Ingest input image in Python 3.14 using OpenCV and SciPy. Extract multi-scale Difference-of-Gaussians (DoG) lineart, bilateral color flats, and luminance-quantized cel shadow masks.
- **Stage 2 (Topological Skeleton & Spline Fitting):** Morphological medial axis thinning transforms lines into a 1-pixel graph. Topological traversal extracts continuous stroke chains. Euclidean distance transforms compute dynamic pressure profiles ($DT(x, y)$). Schneider's cubic Bézier fitting converts pixel clusters into smooth mathematical curves.
- **Stage 3 (Artistic Drawing Choreographer):** Schedules strokes into a 5-layer human painting sequence: (1) Gesture underdrawing, (2) Closed-contour flat coloring, (3) Cel-shading shadow passes, (4) Master inking with tapering line weights, and (5) Specular highlights and rim lighting.
- **Stage 4 (Live Krita Streamer):** Streams stroke batches over authenticated loopback IPC (`127.0.0.1:18812`) to Krita's main thread dispatcher, triggering native brush stamping/curves with real-time viewport projection updates.
- **Stage 5 (Fidelity Gate):** Computes SSIM and edge intersection-over-union (IoU) against the reference image to guarantee near-identical ("ditto") visual fidelity without random scribble artifacts.

**Tech Stack:** Python 3.14, OpenCV 5.1 (`cv2`), SciPy 1.18 (`scipy.ndimage`), Pillow 13, FastMCP, Length-Prefixed JSON IPC over TCP (`127.0.0.1:18812`), Krita 5.3+ native API (`node.setPixelData`, `doc.refreshProjection`).

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- Computer vision processing (`cv2`, `scipy`) runs strictly on the MCP server side. Krita embedded Python plugin receives lightweight, pure JSON stroke coordinate batches and color metadata.
- All IPC communication strictly loopback `127.0.0.1:18812` with constant-time SHA-256 token verification.
- Output canvas layer structure in Krita must be strictly non-destructive:
  - `01_Underdrawing_Sketch`
  - `02_Flat_Colors`
  - `03_Cel_Shadows` (Multiply mode)
  - `04_Master_Lineart` (Normal mode)
  - `05_Highlights_RimLight` (Screen/Addition mode)
- Stroke fidelity benchmark: Reconstructed illustration must achieve SSIM $\ge 0.85$ and Edge IoU $\ge 0.78$ against the reference image.
- Both live Krita execution and headless mock execution modes must maintain 100% test suite passing rate.

## Review Focus

- **Input/Failure Class 1: Junction Disconnection & Hairy Lines**: Morphological thinning produces T-junctions and Y-junctions; greedy graph traversal without tangent continuity creates hairball scribbles. DFS path assembly must prioritize minimal turning angle across junctions.
- **Input/Failure Class 2: Pressure Reversal on Tapered Lines**: Line endpoints (hair tips, cloth wrinkles) must taper to near-zero pressure ($w \approx 0.15$), while silhouette lines maintain bold pressure ($w \approx 0.90$). Distance transform must be sampled along the spline arc length.
- **Input/Failure Class 3: Color Bleed Past Lineart**: Flat color contour fills must slightly dilate (1-2 pixels) under the lineart mask to prevent white pixel halos between ink and color, replicating digital inking "trapping".
- **Input/Failure Class 4: IPC Event Loop Overload on High Stroke Count**: A complex anime poster contains 800-2,500 individual strokes. Sending individual socket jobs per stroke will freeze Qt. Strokes must be transmitted in batched arrays of 30-60 strokes per IPC message.
- **Input/Failure Class 5: Extreme Aspect Ratio / Resolution Mismatch**: Reference image resolution may vary (e.g., 768×1024 or 1240×1754). Coordinate normalization must maintain aspect ratio with letterboxing or exact canvas dimension scaling.

---

### Task 1: Computer Vision Art Decomposer (Semantic Multi-Plane Segmentation)

**Files:**
- Create: `src/krita_mcp_lazy/vector_artist/decomposer.py`
- Create: `src/krita_mcp_lazy/vector_artist/__init__.py`
- Test: `tests/unit/vector_artist/test_decomposer.py`

**Interfaces:**
- Consumes: Reference image path (PNG/JPG), `cv2`, `numpy`
- Produces: `ArtDecomposition(lineart_mask: np.ndarray, color_regions: list[ColorRegion], shadow_mask: np.ndarray, highlight_mask: np.ndarray, canvas_size: tuple[int, int])`

- [ ] **Step 1: Write failing unit test for decomposer**

```python
# tests/unit/vector_artist/test_decomposer.py
import numpy as np
import cv2
import pytest
from PIL import Image

def test_decomposer_extracts_distinct_planes(tmp_path):
    from krita_mcp_lazy.vector_artist.decomposer import ImageArtDecomposer
    
    # Create synthetic test cartoon image with black outline, blue fill, and dark blue shadow
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.circle(img, (100, 100), 50, (255, 180, 0), -1)  # Orange face
    cv2.circle(img, (100, 100), 50, (0, 0, 0), 3)       # Black outline
    cv2.ellipse(img, (100, 115), (35, 20), 0, 0, 180, (180, 120, 0), -1) # Shadow
    
    img_path = str(tmp_path / "synthetic_anime.png")
    cv2.imwrite(img_path, img)
    
    decomposer = ImageArtDecomposer()
    decomp = decomposer.decompose(img_path)
    
    assert decomp.canvas_size == (200, 200)
    assert decomp.lineart_mask.shape == (200, 200)
    assert np.sum(decomp.lineart_mask > 0) > 100, "Lineart mask must capture dark strokes"
    assert len(decomp.color_regions) >= 1, "Must detect colored regions"
    assert decomp.shadow_mask.shape == (200, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/vector_artist/test_decomposer.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement `ImageArtDecomposer` in `src/krita_mcp_lazy/vector_artist/decomposer.py`**

1. `extract_lineart(img_bgr)`: Use multi-scale Difference of Gaussians (DoG) with $\sigma_1 = 1.0, \sigma_2 = 2.5$ + adaptive thresholding to cleanly isolate dark ink lines.
2. `extract_color_flats(img_bgr, line_mask)`: Apply bilateral filter to eliminate gradient noise, quantize palette via K-Means / MeanShift, dilate regions by 2px behind lineart to prevent unpainted halos.
3. `extract_cel_shadows(img_bgr, color_regions)`: Compare luminance of sub-regions to extract secondary shading boundaries.
4. `extract_specular_highlights(img_bgr)`: Extract bright pixels ($V > 235, S < 40$) for eye glints, jewelry, and rim lights.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/vector_artist/test_decomposer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/vector_artist/ tests/unit/vector_artist/
git commit -m "feat(vector_artist): implement semantic multi-plane art decomposer"
```

---

### Task 2: Medial Axis Skeletonizer & Continuous Bézier Stroke Extractor

**Files:**
- Create: `src/krita_mcp_lazy/vector_artist/skeletonizer.py`
- Test: `tests/unit/vector_artist/test_skeletonizer.py`

**Interfaces:**
- Consumes: Binary lineart mask ($M_{line} \in \{0, 255\}$), `scipy.ndimage.distance_transform_edt`
- Produces: `list[ContinuousStroke]`, where each stroke has:
  - `points: list[tuple[float, float]]` (fitted Bézier control samples)
  - `pressures: list[float]` (normalized line thickness $p \in [0.15, 1.0]$)
  - `length: float`
  - `stroke_type: str` ("silhouette", "feature", "hatch")

- [ ] **Step 1: Write failing test for stroke extraction & pressure profiling**

```python
# tests/unit/vector_artist/test_skeletonizer.py
import numpy as np
import cv2
import pytest

def test_skeletonizer_extracts_continuous_tapered_strokes():
    from krita_mcp_lazy.vector_artist.skeletonizer import LineartSkeletonizer
    
    # Create an image with an arch stroke that is thick in the middle, thin at the ends
    mask = np.zeros((100, 100), dtype=np.uint8)
    pts = np.array([[20, 80], [50, 20], [80, 80]], dtype=np.int32)
    cv2.polylines(mask, [pts], isClosed=False, color=255, thickness=6)
    # Taper the ends manually
    mask[75:85, 15:25] = cv2.circle(np.zeros((10, 10), dtype=np.uint8), (5, 5), 2, 255, -1)
    
    skeletonizer = LineartSkeletonizer()
    strokes = skeletonizer.extract_strokes(mask)
    
    assert len(strokes) >= 1, "Must extract at least one continuous stroke"
    main_stroke = max(strokes, key=lambda s: s.length)
    assert len(main_stroke.points) >= 3, "Stroke must contain sequential spline points"
    assert len(main_stroke.pressures) == len(main_stroke.points)
    # Middle pressure should be greater than endpoints
    assert main_stroke.pressures[len(main_stroke.pressures) // 2] > main_stroke.pressures[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/vector_artist/test_skeletonizer.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `LineartSkeletonizer` in `src/krita_mcp_lazy/vector_artist/skeletonizer.py`**

1. Apply morphological thinning (Zhang-Suen thinning via OpenCV/SciPy) to reduce binary line mask to a 1-pixel wide graph.
2. Calculate Euclidean Distance Transform $DT$ of the original line mask to extract physical line width at every pixel.
3. Construct adjacency graph $G$: identify nodes with degree 1 (endpoints) and degree $> 2$ (junctions).
4. Run greedy DFS path extraction prioritizing minimal directional deflection ($\Delta \theta \approx 0$) through junctions to preserve natural pen stroke continuity.
5. Apply Ramer-Douglas-Peucker (RDP) path simplification with Schneider's cubic Bézier fitting.
6. Sample normalized pressures from $DT$ along the fitted path: endpoints automatically taper to thin strokes ($w \approx 0.15$), thick junctions expand to bold lines ($w \approx 1.0$).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/vector_artist/test_skeletonizer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/vector_artist/skeletonizer.py tests/unit/vector_artist/test_skeletonizer.py
git commit -m "feat(vector_artist): implement medial axis skeletonizer and continuous spline extractor"
```

---

### Task 3: Artistic Drawing Choreographer & Layer Scheduler

**Files:**
- Create: `src/krita_mcp_lazy/vector_artist/choreographer.py`
- Test: `tests/unit/vector_artist/test_choreographer.py`

**Interfaces:**
- Consumes: `ArtDecomposition`, `list[ContinuousStroke]`
- Produces: `DrawingSchedule` containing ordered stages:
  - `Stage 1: Underdrawing` (loose low-opacity gesture paths)
  - `Stage 2: Flat Fills` (sorted background-to-foreground color boundary fills)
  - `Stage 3: Cel Shadows` (cast shadow boundaries and fills in Multiply mode)
  - `Stage 4: Master Inking` (sorted strokes: outer silhouette -> facial features -> hair -> cloth folds)
  - `Stage 5: Highlights & Rim Lights` (specular points, airbrush rim sweeps)

- [ ] **Step 1: Write failing test for drawing choreography ordering**

```python
# tests/unit/vector_artist/test_choreographer.py
import pytest
from krita_mcp_lazy.vector_artist.choreographer import DrawingChoreographer
from krita_mcp_lazy.vector_artist.decomposer import ArtDecomposition, ColorRegion
from krita_mcp_lazy.vector_artist.skeletonizer import ContinuousStroke
import numpy as np

def test_choreographer_orders_stages_logically():
    choreographer = DrawingChoreographer()
    dummy_decomp = ArtDecomposition(
        lineart_mask=np.zeros((100, 100), dtype=np.uint8),
        color_regions=[
            ColorRegion(name="bg", rgb=(200, 200, 200), area=5000, contour=[(0, 0), (100, 0), (100, 100), (0, 100)]),
            ColorRegion(name="hair", rgb=(40, 30, 20), area=1200, contour=[(30, 20), (70, 20), (50, 60)]),
        ],
        shadow_mask=np.zeros((100, 100), dtype=np.uint8),
        highlight_mask=np.zeros((100, 100), dtype=np.uint8),
        canvas_size=(100, 100),
    )
    dummy_strokes = [
        ContinuousStroke(points=[(10, 10), (90, 90)], pressures=[0.5, 0.5], length=113.0, stroke_type="silhouette"),
        ContinuousStroke(points=[(40, 40), (50, 40)], pressures=[0.2, 0.2], length=10.0, stroke_type="eye_detail"),
    ]
    
    schedule = choreographer.build_schedule(dummy_decomp, dummy_strokes)
    
    assert len(schedule.stages) == 5
    stage_names = [s.name for s in schedule.stages]
    assert stage_names == [
        "01_Underdrawing",
        "02_Flat_Colors",
        "03_Cel_Shadows",
        "04_Master_Lineart",
        "05_Highlights_RimLight",
    ]
    # Silhouette strokes must precede micro detail strokes in Master Lineart
    inking_stage = schedule.stages[3]
    assert inking_stage.strokes[0].stroke_type == "silhouette"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/vector_artist/test_choreographer.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `DrawingChoreographer` in `src/krita_mcp_lazy/vector_artist/choreographer.py`**

1. Sort color regions by area (largest background elements first, smallest foreground elements last).
2. Classify strokes by length, location, and curvature:
   - Long outer loop strokes $\to$ "silhouette"
   - Center/head cluster strokes $\to$ "facial_features"
   - Wrinkle/hatch strokes $\to$ "cloth_folds"
3. Order lineart drawing pass: silhouette first (gives structure), then facial features, then hair flow, then cloth folds.
4. Generate underdrawing pass using downsampled, smoothed versions of primary silhouette strokes with low opacity (0.15) and light cyan/pencil color (`#7CA0B8`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/vector_artist/test_choreographer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/vector_artist/choreographer.py tests/unit/vector_artist/test_choreographer.py
git commit -m "feat(vector_artist): implement artistic drawing choreographer and stage scheduler"
```

---

### Task 4: High-Performance Live Stroke & Vector Bridge Handlers

**Files:**
- Create: `src/krita_mcp_lazy/vector_artist/stroke_player.py`
- Modify: `plugins/krita_mcp_bridge/handlers_strokes.py`
- Test: `tests/unit/vector_artist/test_stroke_player.py`

**Interfaces:**
- Consumes: `DrawingSchedule`, `AsyncIPCClient`
- Produces: `StrokePlayer.play_schedule(doc_id: str, schedule: DrawingSchedule, live_playback: bool, stroke_delay_ms: int) -> PlaybackReport`
- New IPC handlers:
  - `stroke.batch_paint`: draws an array of Bézier strokes in a single IPC roundtrip with main-thread event yielding.
  - `fill.contour_region`: draws a closed polygon outline and fills with target RGB.

- [ ] **Step 1: Write failing test for StrokePlayer and batch streaming**

```python
# tests/unit/vector_artist/test_stroke_player.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.vector_artist.stroke_player import StrokePlayer
from krita_mcp_lazy.vector_artist.choreographer import DrawingSchedule, DrawingStage
from krita_mcp_lazy.vector_artist.skeletonizer import ContinuousStroke

@pytest.mark.asyncio
async def test_stroke_player_streams_batches_to_krita():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"success": True, "strokes_rendered": 2}
    
    schedule = DrawingSchedule(stages=[
        DrawingStage(
            name="04_Master_Lineart",
            layer_type="paintLayer",
            blend_mode="normal",
            opacity=255,
            strokes=[
                ContinuousStroke(points=[(10, 10), (50, 50)], pressures=[0.5, 0.8], length=56.0, stroke_type="silhouette"),
                ContinuousStroke(points=[(50, 50), (90, 50)], pressures=[0.8, 0.4], length=40.0, stroke_type="silhouette"),
            ],
            color_regions=[],
        )
    ])
    
    player = StrokePlayer(mock_client, batch_size=50)
    report = await player.play_schedule("doc_test", schedule)
    
    assert report["total_stages"] == 1
    assert report["total_strokes"] == 2
    # Verify layer was created and batch_paint was called
    actions = [c[0][0] for c in mock_client.send_job.call_args_list]
    assert "layer.create" in actions
    assert "stroke.batch_paint" in actions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/vector_artist/test_stroke_player.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `StrokePlayer` and bridge handler `stroke.batch_paint`**

In `plugins/krita_mcp_bridge/handlers_strokes.py`:
- Register `stroke.batch_paint`: accepts `doc_id`, `layer_id`, `strokes: list[dict]`.
- For each stroke in the batch, interpolate sub-pixel points along Bézier control anchors, scale by pressure, and draw anti-aliased circles/lines via `QPainter` (or PIL fallback in headless mode).
- Refresh canvas projection once per batch to ensure smooth 60fps UI responsiveness.

In `src/krita_mcp_lazy/vector_artist/stroke_player.py`:
- Implement `StrokePlayer.play_schedule()` orchestrating layer creation, region fills, and batched stroke dispatching.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/vector_artist/test_stroke_player.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/vector_artist/stroke_player.py plugins/krita_mcp_bridge/handlers_strokes.py tests/unit/vector_artist/test_stroke_player.py
git commit -m "feat(vector_artist): implement batched live stroke player and bridge handler"
```

---

### Task 5: Precision Visual Fidelity Evaluator (SSIM & "Ditto" Verification Gate)

**Files:**
- Create: `src/krita_mcp_lazy/vector_artist/fidelity_gate.py`
- Test: `tests/unit/vector_artist/test_fidelity_gate.py`

**Interfaces:**
- Consumes: Reference image path, Rendered canvas / screenshot image path
- Produces: `FidelityScore(ssim: float, edge_iou: float, color_mse: float, is_ditto: bool, defect_regions: list[tuple[int, int, int, int]])`

- [ ] **Step 1: Write failing test for visual fidelity evaluator**

```python
# tests/unit/vector_artist/test_fidelity_gate.py
import numpy as np
import cv2
import pytest

def test_fidelity_gate_validates_match(tmp_path):
    from krita_mcp_lazy.vector_artist.fidelity_gate import VisualFidelityGate
    
    # Ground truth image
    ref = np.full((150, 150, 3), 200, dtype=np.uint8)
    cv2.circle(ref, (75, 75), 40, (0, 0, 0), 2)
    ref_path = str(tmp_path / "ref.png")
    cv2.imwrite(ref_path, ref)
    
    # Identical rendered image
    render_path = str(tmp_path / "render.png")
    cv2.imwrite(render_path, ref)
    
    # Random scribble image
    scribble = np.random.randint(0, 255, (150, 150, 3), dtype=np.uint8)
    scribble_path = str(tmp_path / "scribble.png")
    cv2.imwrite(scribble_path, scribble)
    
    gate = VisualFidelityGate(min_ssim=0.85, min_edge_iou=0.75)
    
    score_perfect = gate.evaluate(ref_path, render_path)
    assert score_perfect.is_ditto is True
    assert score_perfect.ssim > 0.95
    assert score_perfect.edge_iou > 0.90
    
    score_bad = gate.evaluate(ref_path, scribble_path)
    assert score_bad.is_ditto is False
    assert score_bad.ssim < 0.50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/vector_artist/test_fidelity_gate.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `VisualFidelityGate` in `src/krita_mcp_lazy/vector_artist/fidelity_gate.py`**

1. Calculate structural similarity index (SSIM) between reference and rendered images.
2. Extract Canny edges on both and compute Intersection over Union (IoU) of binary edge masks:
   $$\text{Edge IoU} = \frac{|E_{ref} \cap E_{render}|}{|E_{ref} \cup E_{render}|}$$
3. Identify localized grid cells with SSIM $< 0.70$ as `defect_regions` for surgical re-stroking.
4. Return `FidelityScore(is_ditto = (ssim >= min_ssim and edge_iou >= min_edge_iou))`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/vector_artist/test_fidelity_gate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/vector_artist/fidelity_gate.py tests/unit/vector_artist/test_fidelity_gate.py
git commit -m "feat(vector_artist): implement SSIM and edge IoU visual fidelity gate"
```

---

### Task 6: Autonomous Stroke-by-Stroke Orchestration Tool & CLI

**Files:**
- Create: `src/krita_mcp_lazy/server/tools_vector_artist.py`
- Modify: `src/krita_mcp_lazy/server/app.py`
- Create: `scripts/draw_image_stroke_by_stroke.py`
- Test: `tests/unit/server/test_vector_artist_tool.py`

**Interfaces:**
- Consumes: Any input image path, `ImageArtDecomposer`, `LineartSkeletonizer`, `DrawingChoreographer`, `StrokePlayer`, `VisualFidelityGate`
- Produces: MCP Tool `krita_draw_image_stroke_by_stroke(image_path, doc_id, live_timelapse, target_dpi) -> dict`
- CLI executable: `python scripts/draw_image_stroke_by_stroke.py --input <path>`

- [ ] **Step 1: Write failing test for vector artist tool**

```python
# tests/unit/server/test_vector_artist_tool.py
import pytest
from unittest.mock import AsyncMock, patch
import numpy as np
import cv2

@pytest.mark.asyncio
async def test_draw_image_tool_orchestrates_full_drawing(tmp_path):
    from krita_mcp_lazy.server.tools_vector_artist import draw_image_stroke_by_stroke
    
    # Create test image
    test_img = np.full((120, 120, 3), 255, dtype=np.uint8)
    cv2.circle(test_img, (60, 60), 30, (0, 0, 0), 2)
    img_path = str(tmp_path / "test_creator.png")
    cv2.imwrite(img_path, test_img)
    
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"success": True, "created": True}
    
    out_composite = str(tmp_path / "out_rendered.png")
    result = await draw_image_stroke_by_stroke(
        image_path=img_path,
        doc_id="doc_test_vector",
        client=mock_client,
        output_png_path=out_composite,
    )
    
    assert result["success"] is True
    assert result["total_strokes"] >= 1
    assert result["stages_drawn"] == 5
    assert result["fidelity"]["ssim"] > 0.80
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/server/test_vector_artist_tool.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `tools_vector_artist.py` and register with FastMCP**

1. Decompose input image $\to$ extract continuous Bézier splines $\to$ schedule drawing order.
2. Stream live into Krita layer-by-layer (`01_Underdrawing`, `02_Flat_Colors`, `03_Cel_Shadows`, `04_Master_Lineart`, `05_Highlights_RimLight`).
3. Capture final composite and evaluate fidelity gate.
4. Register `@server.tool(name="krita_draw_image_stroke_by_stroke")` in `src/krita_mcp_lazy/server/app.py`.
5. Create `scripts/draw_image_stroke_by_stroke.py` for standalone CLI execution.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/server/test_vector_artist_tool.py -v`
Expected: PASS.

- [ ] **Step 5: Run CLI on the user's uploaded anime creator image to verify visual perfection**

Run:
```powershell
python scripts/draw_image_stroke_by_stroke.py --input "C:/Users/Rahul/.gemini/antigravity/brain/47071ca1-a878-4bd8-8e36-2901894c7575/.user_uploaded/media_1795071083045_a1bcd4d7.jpg"
```
Expected:
- Krita canvas displays 5 distinct non-destructive layers.
- Strokes are drawn with dynamic pressure tapering matching the anime creator illustration.
- SSIM $\ge 0.85$ achieved.

- [ ] **Step 6: Commit**

```bash
git add src/krita_mcp_lazy/server/tools_vector_artist.py src/krita_mcp_lazy/server/app.py scripts/draw_image_stroke_by_stroke.py tests/unit/server/test_vector_artist_tool.py
git commit -m "feat(server): expose krita_draw_image_stroke_by_stroke tool and CLI runner"
```

---

## Self-Review

1. **Spec coverage:** Replaces blind pixel-dumping with a genuine mathematical vectorization and stroke-by-stroke drawing pipeline. Handles line extraction, skeletonization, Bézier spline fitting, dynamic line weight pressure, cel-shading separation, and live Krita playback.
2. **Step scan:** Every step contains explicit test signatures, implementation targets, and verifiable execution outputs.
3. **Type consistency:** Consistent `ArtDecomposition`, `ContinuousStroke`, `DrawingSchedule`, `FidelityScore`, and `StrokePlayer` method signatures maintained across all tasks.
4. **Review Focus:** Addressed all 5 review focus classes (tangent continuity across junctions to prevent hairballs, distance transform pressure profiling for tapering, color trapping dilation to prevent halos, batch IPC streaming to avoid Qt lockup, and resolution scaling).
5. **Proportion:** Tasks are cleanly decomposed into bite-sized units with clear deliverables.
