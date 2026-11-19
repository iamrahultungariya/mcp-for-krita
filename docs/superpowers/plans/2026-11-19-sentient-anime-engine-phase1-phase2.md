# Sentient Anime Engine & Live Krita Pipeline (Phase 1 & Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Krita MCP pipeline into an autonomous, self-thinking AI Artist by implementing Phase 1 (Bridge State Oracle, Real Live Canvas Progressive Drawing, and Native In-App Color Grading) and Phase 2 (Authentic Anime Character Anatomy/Hair Clump Engine replacing the stick-figure disaster, 12-Frame Looping Stride Rig, Stadium Parallax, and 10-Second Master Video Assembly).

**Architecture:** 
1. **Sentient Core (Phase 1)**: Proactive socket probe (`BridgeStateOracle`) auto-detects Krita's active document without manual spoonfeeding; `RealLiveCanvasDriver` delivers real-time progressive BGRA stroke rendering into `KisPaintLayer` with live canvas viewport refresh; `InAppColorGrading` injects native Krita adjustment layers (Curves, Color Balance, Bloom).
2. **Anime Artistic Engine (Phase 2)**: Replaces crude OpenCV line/circle stick figures with high-fidelity anime anatomy modeling (Refs 2–5: head-to-body 1:7.5, geometric tapering hair ribbons with angel-ring specular, multi-tone anime eyes, athletic sportswear with fabric tension folds); a 12-frame kinematic stride engine animates squash/stretch with ponytail inertia and sweat particle physics, composited over a 3-plane stadium parallax conveyor for a 10.0-second 24 FPS master MP4.

**Tech Stack:** Python 3.14, FastMCP, Krita 5.x CPython IPC (`127.0.0.1:18812`), PyQt5/PyQt6, OpenCV, Pillow, NumPy.

**Spec:** [docs/superpowers/specs/2026-11-19-sentient-anime-engine-design.md](file:///c:/Users/Rahul/OneDrive/Desktop/Krita%20MCP/docs/superpowers/specs/2026-11-19-sentient-anime-engine-design.md)

## Global Constraints
- **Zero Spoonfeeding**: All operations auto-sense open documents via `BridgeStateOracle`; never require the user to state that Krita is open or specify file IDs unless multiple conflicting documents exist.
- **Byte Order Integrity**: All pixel buffers pushed to Krita must strictly use native little-endian **BGRA** (Blue, Green, Red, Alpha) to prevent washed out or inverted colors.
- **No Stick Figures**: All character geometry must adhere to studio anime grammar (Refs 2, 3, 4, 5). Absolute zero tolerance for OpenCV `cv2.line`/`cv2.circle` primitive stick limbs.
- **Live Canvas Feedback**: Every stroke execution must be written to `KisPaintLayer` and trigger `doc.refreshProjection()` so changes are visibly rendered on the active Krita GUI.
- **In-App Layer Grading**: The `.kra` file must contain editable adjustment layers (`multiply` for cel-shadows, `screen` for glow/rim, adjustment curves for color grade).
- **Exact Video Timing**: Master MP4 deliverable must be exactly 240 frames at 24 FPS ($10.0\text{ seconds}$).

## Review Focus
1. **Bridge Oracle Port Probing**: When Krita is closed, oracle returns `bridge_live=False` within 500ms without crashing; when open, discovers `running.kra` automatically.
2. **Real Drawing Persistence**: `krita_live_tablet_stroke` must actually alter canvas pixel data (verified by reading back non-zero pixel bytes from the target layer).
3. **Color Channel Verification**: Red color `#FF0000` must produce `(0, 0, 255, 255)` in BGRA bytes; no channel inversion.
4. **Anime Character Aesthetic**: The generated character must have facial features (eyes with specular glints, nose-tick, mouth), clumped hair ribbons, and athletic sportswear—not stick lines.
5. **Alpha Inheritance**: Cel shadows must have `inheritAlpha=True` so they clip perfectly to character flats without edge bleed.

---

## Phase 1: Sentient Foundation, Live Drawing & In-App Grading

### Task 1: BridgeStateOracle & Auto-Discovery Handshake

**Files:**
- Create: `src/krita_mcp_lazy/bridge/oracle.py`
- Modify: `plugins/krita_mcp_bridge/handlers_document.py`
- Modify: `src/krita_mcp_lazy/server/tools_document.py`
- Test: `tests/unit/bridge/test_oracle.py`

**Interfaces:**
- Consumes: `socket`, `asyncio`, IPC client.
- Produces: `BridgeStateOracle` with `probe() -> BridgeState`, `get_active_document_context() -> Dict[str, Any]`, and FastMCP tool `krita_auto_sense_context`.

- [ ] **Step 1: Write failing unit test for `BridgeStateOracle`**

```python
# tests/unit/bridge/test_oracle.py
import pytest
from unittest.mock import patch, MagicMock
from krita_mcp_lazy.bridge.oracle import BridgeStateOracle, BridgeState

def test_oracle_reports_disconnected_when_port_closed():
    oracle = BridgeStateOracle(host="127.0.0.1", port=19999)
    state = oracle.probe()
    assert state.bridge_live is False
    assert state.active_document is None

def test_oracle_auto_senses_active_document():
    oracle = BridgeStateOracle(host="127.0.0.1", port=18812)
    with patch.object(oracle, "_query_active_doc", return_value={"name": "running.kra", "width": 3840, "height": 2160}):
        state = oracle.probe(check_doc=True)
        assert state.active_document is not None
        assert state.active_document["name"] == "running.kra"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/bridge/test_oracle.py -v`  
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `BridgeStateOracle` in `src/krita_mcp_lazy/bridge/oracle.py`**

Implement non-blocking socket probe (0.5s timeout) to `127.0.0.1:18812`. If connected, query active document metadata (`document.inspect_active`) via IPC. If socket refused, return `BridgeState(bridge_live=False)`.

- [ ] **Step 4: Update `plugins/krita_mcp_bridge/handlers_document.py`**

Add `document.inspect_active` handler that returns the currently focused document from `app.activeDocument()` with its width, height, resolution, and active node name without needing a `doc_id` parameter.

- [ ] **Step 5: Register FastMCP tool `krita_auto_sense_context` in `tools_document.py`**

Expose `krita_auto_sense_context` so the agent can discover open canvases at the beginning of any interaction.

- [ ] **Step 6: Run test to verify pass**

Run: `pytest tests/unit/bridge/test_oracle.py -v`  
Expected: PASS.

---

### Task 2: Real Progressive Live Canvas Driver with Native BGRA Sanitization

**Files:**
- Modify: `plugins/krita_mcp_bridge/canvas_tablet_driver.py`
- Modify: `plugins/krita_mcp_bridge/handlers_strokes.py`
- Modify: `src/krita_mcp_lazy/server/tools_painting.py`
- Test: `tests/unit/plugin/test_live_canvas_driver.py`

**Interfaces:**
- Consumes: Krita `KisPaintLayer`, `QPainter` / Pillow rasterizer, BGRA conversion.
- Produces: `CanvasTabletDriver.execute_live_stroke()` that actually modifies `KisPaintLayer` pixel data and refreshes the canvas view.

- [ ] **Step 1: Write failing test for real live canvas driver**

```python
# tests/unit/plugin/test_live_canvas_driver.py
import pytest
from plugins.krita_mcp_bridge.canvas_tablet_driver import CanvasTabletDriver

def test_live_stroke_renders_and_returns_bounding_box():
    driver = CanvasTabletDriver()
    points = [
        {"x": 100.0, "y": 100.0, "pressure": 0.2},
        {"x": 150.0, "y": 120.0, "pressure": 0.8},
        {"x": 200.0, "y": 140.0, "pressure": 0.3},
    ]
    result = driver.execute_live_stroke(
        points=points,
        preset_name="f)_Ink-3_Gpen",
        color_hex="#1A365D",
        size=8.0,
        doc_id="test_doc",
        layer_name="Lineart",
    )
    assert result["success"] is True
    assert result["points_drawn"] == 3
    assert "bounding_box" in result
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/plugin/test_live_canvas_driver.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement real canvas painting in `canvas_tablet_driver.py` and `handlers_strokes.py`**

- In `canvas_tablet_driver.py`, replace the dummy stub with real rasterization: calculate bounding box, rasterize pressure-tapered Bézier segments, convert color to native **BGRA**, fetch existing layer bytes, blend with source-over alpha compositing, and push back via `node.setPixelData()`.
- Trigger `doc.refreshProjection()` so the stroke appears live on the Krita screen.
- Ensure proper color translation: `#1A365D` must translate to `(0x5D, 0x36, 0x1A, 0xFF)` in BGRA order.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/plugin/test_live_canvas_driver.py -v`  
Expected: PASS.

---

### Task 3: In-App Krita Color Grading & Adjustment Layer Generator

**Files:**
- Create: `src/krita_mcp_lazy/color_grading/adjustments.py`
- Modify: `plugins/krita_mcp_bridge/handlers_layers.py`
- Modify: `src/krita_mcp_lazy/server/tools_layers.py`
- Test: `tests/unit/color_grading/test_adjustments.py`

**Interfaces:**
- Consumes: Krita layer API, filter masks, adjustment layers.
- Produces: `ColorGradingManager.inject_adjustment_layers(doc_id, profile="golden_hour_anime") -> dict`.

- [ ] **Step 1: Write failing test for color grading adjustment injector**

```python
# tests/unit/color_grading/test_adjustments.py
import pytest
from krita_mcp_lazy.color_grading.adjustments import ColorGradingManager, GradingProfile

def test_generate_golden_hour_grading_spec():
    manager = ColorGradingManager()
    spec = manager.get_profile_spec("golden_hour_anime")
    assert spec.warm_highlight_tint == "#FFF3B0"
    assert spec.deep_shadow_tint == "#1E152A"
    assert len(spec.layers) >= 2
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/color_grading/test_adjustments.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement `ColorGradingManager` in `src/krita_mcp_lazy/color_grading/adjustments.py`**

Define studio anime color profiles:
- `golden_hour_anime`: Warm sun rim highlight (screen blend 60%), cool violet cel shadows (multiply blend 75%), S-curve contrast adjustment layer.
- `dusk_cinematic`: Cyan backlight with deep magenta ambient occlusion.

- [ ] **Step 4: Update `plugins/krita_mcp_bridge/handlers_layers.py`**

Add handler `layer.create_adjustment` supporting Krita's `adjustmentLayer` type with filter configuration (e.g. `cross_channel`, `colorbalance`, `curves`).

- [ ] **Step 5: Register FastMCP tool `krita_apply_color_grading` in `tools_layers.py`**

- [ ] **Step 6: Run test to verify pass**

Run: `pytest tests/unit/color_grading/test_adjustments.py -v`  
Expected: PASS.

---

## Phase 2: Autonomous Anime Character Engine, Rig & 10s Animation

### Task 4: Anime Character Anatomy & Hair Clump Generator (Replacing Stick Figures)

**Files:**
- Create: `src/krita_mcp_lazy/character/anime_artist_engine.py`
- Modify: `src/krita_mcp_lazy/animation/athletic_character_rig.py`
- Test: `tests/unit/character/test_anime_artist_engine.py`

**Interfaces:**
- Consumes: Anime design principles from uploaded references (proportions 1:7.5, geometric ribbon hair, dual-highlight eyes).
- Produces: `AnimeCharacterArtEngine.render_character_component(...)` generating production-grade anime layers (flats, cel-shadows, lineart, rim).

- [ ] **Step 1: Write failing test for anime character anatomy generator**

```python
# tests/unit/character/test_anime_artist_engine.py
import pytest
import numpy as np
from krita_mcp_lazy.character.anime_artist_engine import AnimeCharacterArtEngine, CharacterPose

def test_anime_character_renders_facial_features_and_hair_ribbons():
    engine = AnimeCharacterArtEngine(width=1920, height=1080)
    pose = CharacterPose(torso_tilt_deg=14.0, head_pitch_deg=5.0)
    layers = engine.render_cel_layers(pose)
    
    assert "Lineart" in layers
    assert "Flats" in layers
    assert "Cel_Shadows" in layers
    assert "Hair_Specular" in layers
    
    # Verify non-trivial drawing content
    lineart_arr = layers["Lineart"]
    assert np.count_nonzero(lineart_arr[:, :, 3]) > 1000
    # Verify hair ribbons are drawn with width and shape, not 1D stick lines
    hair_arr = layers["Flats"]
    assert np.count_nonzero(hair_arr[:, :, 3]) > 5000
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/character/test_anime_artist_engine.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement `AnimeCharacterArtEngine` in `src/krita_mcp_lazy/character/anime_artist_engine.py`**

Build authentic anime drawing primitives:
1. **Facial Architecture (Refs 3 & 5)**: Sharp jawline, triangular chin, anime eye contours with upper thick lash line, pupil depth, dual white specular glints, nose tick with cast shadow, defined lips.
2. **Hair Ribbon Clumping (Refs 3 & 4)**: Flowing ponytail and bangs formed of tapered polygonal locks (ribbon masses) with secondary curve arcs, highlighted with a golden-hour specular halo ("angel ring"). No single OpenCV lines!
3. **Athletic Apparel**: Cobalt navy running tank top with white piping curves, running shorts with lateral slit, defined knee joints, sports trainers with sole treads and laces.
4. **Cel-Shading Geometry**: Trapped cast shadows under hair onto forehead, under jaw onto neck, and tension folds along the waist and knees.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/character/test_anime_artist_engine.py -v`  
Expected: PASS.

---

### Task 5: 12-Frame Looping Athletic Stride Kinematic Engine

**Files:**
- Rewrite: `src/krita_mcp_lazy/animation/run_cycle_engine.py`
- Test: `tests/unit/animation/test_run_cycle_engine.py`

**Interfaces:**
- Consumes: `AnimeCharacterArtEngine`, `StridePose`.
- Produces: `RunCycleEngine.render_stride_cycle(width, height) -> List[Dict[str, np.ndarray]]` returning 12 production-grade anime frames.

- [ ] **Step 1: Write failing test for 12-frame anime stride cycle**

```python
# tests/unit/animation/test_run_cycle_engine.py
import pytest
from krita_mcp_lazy.animation.run_cycle_engine import RunCycleEngine

def test_stride_cycle_generates_12_rich_anime_frames():
    engine = RunCycleEngine(width=1920, height=1080)
    frames = engine.generate_all_stride_frames()
    assert len(frames) == 12
    for idx, f in enumerate(frames):
        assert f.shape == (1080, 1920, 4)
        # Verify alpha content exists on every frame
        assert f[:, :, 3].sum() > 0
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/animation/test_run_cycle_engine.py -v`  
Expected: FAIL.

- [ ] **Step 3: Rewrite `src/krita_mcp_lazy/animation/run_cycle_engine.py`**

- Remove all primitive `cv2.line` stick limb rendering and `draw_segment` stick logic.
- Integrate `AnimeCharacterArtEngine` to deform and render proper volumetric anime limbs, clothing meshes, and flowing hair for each of the 12 kinematic stride phases (Contact, Recoil, Passing, Air Peak, Descent).
- Include hair inertia delay ($\Delta x, \Delta y$) and torso squash/stretch vertical bobbing.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/animation/test_run_cycle_engine.py -v`  
Expected: PASS.

---

### Task 6: Multi-Plane Stadium Parallax Scaffolder & Dynamic Sweat Physics

**Files:**
- Modify: `src/krita_mcp_lazy/animation/cinematic_stadium_builder.py`
- Modify: `src/krita_mcp_lazy/animation/cinematic_video_renderer.py`
- Test: `tests/unit/animation/test_stadium_builder.py`

**Interfaces:**
- Consumes: Parallax displacement math, particle physics.
- Produces: Multi-plane stadium backgrounds + parabolic sweat droplets with air drag and sunlight glint.

- [ ] **Step 1: Write failing test for stadium parallax and sweat simulation**

```python
# tests/unit/animation/test_stadium_builder.py
import pytest
from krita_mcp_lazy.animation.cinematic_stadium_builder import StadiumParallaxEngine

def test_stadium_parallax_plane_shifts():
    engine = StadiumParallaxEngine(width=1920, height=1080)
    frame_0 = engine.composite_background(frame_index=0)
    frame_24 = engine.composite_background(frame_index=24)
    assert frame_0.shape == (1080, 1920, 3)
    assert frame_24.shape == (1080, 1920, 3)
    # Track lane displacement check
    assert not (frame_0 == frame_24).all()
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/animation/test_stadium_builder.py -v`  
Expected: FAIL.

- [ ] **Step 3: Update `cinematic_stadium_builder.py` & `cinematic_video_renderer.py`**

- Enhance stadium planes: Sky gradient with morning lens flare, grandstand bleachers with vibrant green turf infield, rich terracotta red polyurethane running track with perspective lane markers.
- Implement realistic sweat emitter: droplets eject backwards with air drag, gravity acceleration, and golden sunlight highlights.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/animation/test_stadium_builder.py -v`  
Expected: PASS.

---

### Task 7: Master 10-Second Video Assembly & Live Krita Scaffolding Pipeline

**Files:**
- Create: `scripts/render_sentient_anime_master.py`
- Modify: `src/krita_mcp_lazy/animation/cinematic_video_renderer.py`
- Test: `tests/unit/animation/test_video_renderer.py`

**Interfaces:**
- Consumes: FastMCP tools, `BridgeStateOracle`, `RunCycleEngine`, `StadiumParallaxEngine`.
- Produces:
  1. Complete layered canvas in Krita (`running.kra`).
  2. 10.0-second master MP4 video deliverable (`output/anime_running_10s_master.mp4`, 240 frames, 24 FPS, high-chroma golden hour grade).

- [ ] **Step 1: Write failing test for master video renderer**

```python
# tests/unit/animation/test_video_renderer.py
import pytest
import os
from krita_mcp_lazy.animation.cinematic_video_renderer import render_master_10s_anime_video

def test_master_video_duration_and_resolution(tmp_path):
    output_mp4 = str(tmp_path / "test_run.mp4")
    # Quick 12-frame smoke test
    res = render_master_10s_anime_video(
        output_mp4_path=output_mp4,
        total_frames=12,
        fps=24,
        width=640,
        height=360,
    )
    assert res["success"] is True
    assert os.path.exists(output_mp4)
    assert os.path.getsize(output_mp4) > 1000
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/animation/test_video_renderer.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement `scripts/render_sentient_anime_master.py`**

Pipeline workflow:
1. Probe Krita via `BridgeStateOracle`. If live, scaffold the 6 semantic anime layers into open canvas with native BGRA bytes.
2. Generate the 12-frame anime character stride cycle using `AnimeCharacterArtEngine`.
3. Loop the 12-frame cycle across 240 frames ($10.0\text{s}$) with continuous stadium parallax conveyor movement, speed lines, camera impact bob, and dynamic flying sweat particles.
4. Encode to high-definition H.264 MP4 (`output/anime_running_10s_master.mp4`).
5. Save native `.kra` project and verify duration and visual fidelity.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/animation/test_video_renderer.py -v`  
Expected: PASS.

- [ ] **Step 5: Execute full end-to-end master render**

Run: `python scripts/render_sentient_anime_master.py`  
Verify: Generate `output/anime_running_10s_master.mp4` and update live Krita document.
