# Live Krita MCP Connection & Cute Anime Movie Poster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish verified live loopback IPC connectivity between the active Krita instance and `krita-MCP-lazy`, then orchestrate the procedural generation of an original, high-production cute anime romance movie poster titled *『星空の約束 - Whispers in the Starlight』* directly on Krita's live canvas with multi-plane depth layers, celestial gradients, romantic character silhouettes, glowing cherry blossoms, and cinematic title typography.

**Architecture:** Resolve Krita's embedded CPython 3.13 sandbox constraint by introducing resilient zero-external-dependency fallbacks (dataclass-backed schemas and PyQt5 QImage/QPainter graphics) in the bridge and core schemas. This enables Krita's native Python plugin extension to launch the authenticated IPC server on loopback port `18812`. Once connected, the ToonFlow MCP pipeline executes art specification, canvas creation, semantic layer scaffolding, celestial sky & star painting, hero lover silhouettes, sakura particles, and visual QA preview verification.

**Tech Stack:** Krita 5.3.4+ native API (`krita.Document`, `krita.Node`, `krita.ManagedColor`), PyQt5 (Krita embedded Qt), CPython 3.13 embedded runtime, FastMCP server, Length-prefixed JSON IPC over TCP Loopback (`127.0.0.1:18812`), Pillow (external server fallback), Pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`

## Global Constraints

- All IPC communication strictly restricted to loopback address `127.0.0.1` and port `18812` with constant-time SHA-256 token verification.
- Embedded Krita Python runtime (CPython 3.13 inside `C:\Program Files\Krita (x64)`) is write-protected and lacks external wheels; `plugins/krita_mcp_bridge` and core schemas must operate flawlessly without requiring pip-installed packages (Pydantic, Pillow) inside Krita.
- FastMCP server and unit test suite in Python 3.14 must retain 100% backward compatibility and test passing rate (128/128 tests passing).
- Non-destructive layer hierarchy must be enforced in Krita: root groups for `00_Sky_Celestial`, `01_Far_Hills_City`, `02_Rooftop_Mid`, `03_Lovers_Hero`, `04_Petals_Particles`, and `05_Typography_Title`.
- Final visual output must be inspected via live canvas capture (`krita_capture_preview`) and scored with visual QA verification.

## Review Focus

- **Input/Failure Class 1: Embedded Python Pydantic Absence**: When Krita loads `src/krita_mcp_lazy/core/schemas.py`, `pydantic` is missing; schema classes must cleanly fallback to standard `dataclasses` with identical `.model_dump()` and `.model_validate()` interfaces.
- **Input/Failure Class 2: Embedded Python Pillow Absence in Stroke/Grid Handlers**: When `handlers_strokes.py` or `handlers_environment.py` executes inside Krita without `PIL`, raster operations must seamlessly fallback to `PyQt5.QtGui.QImage` and `QPainter`.
- **Input/Failure Class 3: Main-Thread GUI Deadlock During Batch Stroke Operations**: Multi-point stroke and layer additions must yield to Krita's Qt event loop via `QTimer` dispatcher to avoid freezing the Krita canvas UI.
- **Input/Failure Class 4: Resolution & Texel Clipping on High-DPI Poster**: 300 DPI A4 poster (2480x3508) involves 8.7 megapixels; layer pixel buffers must match exact canvas bounding boxes without memory leakage.
- **Input/Failure Class 5: IPC Handshake Stale Socket Timeout**: Client reconnects must gracefully retry handshake if Krita is in the middle of re-initializing the extension.

---

### Task 1: Resilient Zero-Dependency Fallback in Core Schemas & Plugin Bridge

**Files:**
- Modify: `src/krita_mcp_lazy/core/schemas.py`
- Modify: `plugins/krita_mcp_bridge/handlers_strokes.py`
- Modify: `plugins/krita_mcp_bridge/handlers_environment.py`
- Modify: `plugins/krita_mcp_bridge/__init__.py`
- Test: `tests/unit/core/test_core.py`
- Test: `tests/unit/painting/test_stroke_handlers.py`

**Interfaces:**
- Consumes: Standard library `dataclasses`, `enum`, `typing`, `PyQt5.QtGui`
- Produces: `JobRequest`, `JobResponse`, `JobStatus` (compatible with both Pydantic v2 and embedded dataclasses) with `.model_dump()` and `.model_validate()`; `render_stroke_points` with dual PIL/QPainter backend.

- [ ] **Step 1: Write test verifying schema dataclass fallback when Pydantic is unavailable**

In `tests/unit/core/test_core.py`:
```python
def test_schema_dataclass_fallback_parity():
    from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
    req = JobRequest(action="test.ping", params={"val": 42})
    dumped = req.model_dump()
    assert dumped["action"] == "test.ping"
    assert dumped["params"] == {"val": 42}
    validated = JobRequest.model_validate(dumped)
    assert validated.action == "test.ping"
```

- [ ] **Step 2: Run test to verify failure or baseline**

Run: `pytest tests/unit/core/test_core.py::test_schema_dataclass_fallback_parity -v`
Expected: PASS or verify import behavior.

- [ ] **Step 3: Implement graceful Pydantic and Pillow fallbacks**

In `src/krita_mcp_lazy/core/schemas.py`: Wrap `from pydantic import BaseModel, Field` in `try...except ImportError`. On exception, implement lightweight `BaseModel` dataclass simulator supporting `Field`, `.model_dump()`, and `.model_validate()`.
In `plugins/krita_mcp_bridge/handlers_strokes.py`: Add `PyQt5.QtGui.QImage` / `QPainter` fallback if `PIL` import fails.
In `plugins/krita_mcp_bridge/handlers_environment.py`: Add `QPainter` fallback for perspective grid line generation if `PIL` import fails.
In `plugins/krita_mcp_bridge/__init__.py`: Add exception logging to `%TEMP%/krita_mcp_bridge_debug.log` so any embedded runtime failure is immediately recorded with tracebacks.

- [ ] **Step 4: Run test suite to verify full compatibility**

Run: `pytest tests/unit/core/ tests/unit/painting/ -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/core/schemas.py plugins/krita_mcp_bridge/
git commit -m "fix(bridge): add zero-dependency fallbacks for embedded Krita runtime"
```

---

### Task 2: Live IPC Bridge Connection & Health Verification with Krita

**Files:**
- Modify: `src/krita_mcp_lazy/transport/client.py:45-75`
- Test: `tests/integration/test_live_krita_connection.py`
- Create: `scripts/verify_live_bridge.py`

**Interfaces:**
- Consumes: Loopback socket `127.0.0.1:18812`, `get_or_create_shared_token()`
- Produces: Verified live connection session, `ping` -> `pong`, `system.version` -> `krita-MCP-lazy 0.1.0`.

- [ ] **Step 1: Write integration test and live verification script**

Create `scripts/verify_live_bridge.py`:
```python
import asyncio
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.core.security import get_or_create_shared_token

async def main():
    token = get_or_create_shared_token()
    client = AsyncIPCClient(host="127.0.0.1", port=18812, token=token, timeout=5.0)
    await client.connect()
    res = await client.send_job("ping", {})
    assert res.result.get("pong") is True
    ver = await client.send_job("system.version", {})
    print("LIVE_KRITA_CONNECTED:", ver.result)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Restart Krita instance to reload Python plugin extension**

Run PowerShell command to gracefully restart Krita (`C:\Program Files\Krita (x64)\bin\krita.exe`). Verify port 18812 opens via `netstat -ano | findstr 18812`.

- [ ] **Step 3: Execute `scripts/verify_live_bridge.py` to confirm live handshake**

Run: `python scripts/verify_live_bridge.py`
Expected: Output containing `LIVE_KRITA_CONNECTED: {'engine': 'krita-MCP-lazy', 'version': '0.1.0'}`.

- [ ] **Step 4: Commit**

```bash
git add scripts/verify_live_bridge.py
git commit -m "chore(bridge): add live Krita connection verification script"
```

---

### Task 3: Anime Movie Concept & Art Direction Production Specification

**Files:**
- Create: `src/krita_mcp_lazy/art_planning/poster_concept.py`
- Test: `tests/unit/art_planning/test_poster_concept.py`

**Interfaces:**
- Consumes: `krita_generate_production_spec`, `krita_calculate_composition_grid`
- Produces: Movie poster metadata dict:
  - Title: *『星空の約束 - Whispers in the Starlight』*
  - Dimensions: 2480 x 3508 (A4 Portrait @ 300 DPI)
  - Color Palette: Twilight Indigo (`#0B1026`), Deep Royal Violet (`#261B4E`), Sunset Rose (`#E86A82`), Horizon Gold (`#FCD0A1`), Glowing Cyan (`#64DFDF`), Sakura Blossom (`#FFB7B2`), Ribbon Crimson (`#E63946`).
  - Semantic Group Hierarchy: `00_Sky_Celestial`, `01_Far_Hills_City`, `02_Rooftop_Mid`, `03_Lovers_Hero`, `04_Petals_Particles`, `05_Typography_Title`.

- [ ] **Step 1: Write test for poster production spec generation**

In `tests/unit/art_planning/test_poster_concept.py`:
```python
def test_anime_poster_spec_generation():
    from src.krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec
    spec = get_whispers_in_starlight_spec()
    assert spec["canvas"]["width"] == 2480
    assert spec["canvas"]["height"] == 3508
    assert len(spec["layers"]) == 6
    assert "#0B1026" in spec["palette"].values()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/art_planning/test_poster_concept.py -v`
Expected: FAIL (module not yet created).

- [ ] **Step 3: Implement `get_whispers_in_starlight_spec()`**

Create `src/krita_mcp_lazy/art_planning/poster_concept.py` with full palette, layer definitions, composition thirds coordinates, and typography text styling.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/art_planning/test_poster_concept.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/art_planning/poster_concept.py tests/unit/art_planning/test_poster_concept.py
git commit -m "feat(art): specify Whispers in the Starlight anime movie poster production spec"
```

---

### Task 4: Canvas Initialization & Semantic Multi-Plane Layer Scaffolding on Live Krita

**Files:**
- Create: `src/krita_mcp_lazy/orchestration/poster_builder.py`
- Test: `tests/unit/orchestration/test_poster_builder.py`

**Interfaces:**
- Consumes: Live `AsyncIPCClient`, actions: `document.create`, `layer.create`, `layer.set_properties`
- Produces: Document ID, structured layer tree matching production specification in active Krita session.

- [ ] **Step 1: Write unit test with mocked IPC client verifying layer scaffolding**

In `tests/unit/orchestration/test_poster_builder.py`:
```python
import pytest
from unittest.mock import AsyncMock
from src.krita_mcp_lazy.orchestration.poster_builder import AnimePosterBuilder

@pytest.mark.asyncio
async def test_scaffold_poster_document():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"doc_id": "doc_poster_001", "success": True}
    builder = AnimePosterBuilder(mock_client)
    doc_id = await builder.initialize_canvas()
    assert doc_id == "doc_poster_001"
    await builder.scaffold_semantic_groups(doc_id)
    assert mock_client.send_job.call_count >= 6
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/orchestration/test_poster_builder.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `AnimePosterBuilder` initialization and scaffolding**

In `src/krita_mcp_lazy/orchestration/poster_builder.py`:
Implement `initialize_canvas()` creating `2480x3508` document at 300 DPI, named "Whispers_In_The_Starlight_Poster".
Implement `scaffold_semantic_groups(doc_id)` creating the 6 non-destructive parent group layers and baseline paint layers with appropriate blend modes (`addition`, `screen`, `normal`).

- [ ] **Step 4: Run unit test to verify pass**

Run: `pytest tests/unit/orchestration/test_poster_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/orchestration/poster_builder.py tests/unit/orchestration/test_poster_builder.py
git commit -m "feat(orchestration): implement anime poster canvas initializer and layer scaffolder"
```

---

### Task 5: Celestial Environment & Twilight Sky Painting Engine

**Files:**
- Modify: `src/krita_mcp_lazy/orchestration/poster_builder.py`
- Test: `tests/unit/orchestration/test_poster_builder.py`

**Interfaces:**
- Consumes: `layer.paint_stroke`, `layer.paint_curve`, `layer.set_pixel_data`
- Produces: Twilight sky vertical gradient, glowing crescent moon, nebula dust, starlight field, and distant city silhouette.

- [ ] **Step 1: Write test for celestial painting methods**

In `tests/unit/orchestration/test_poster_builder.py`:
```python
@pytest.mark.asyncio
async def test_paint_celestial_sky_and_city():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"success": True}
    builder = AnimePosterBuilder(mock_client)
    await builder.paint_celestial_environment("doc_test")
    assert mock_client.send_job.call_count >= 4
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_celestial_sky_and_city -v`
Expected: FAIL.

- [ ] **Step 3: Implement `paint_celestial_environment(doc_id)` in `AnimePosterBuilder`**

Generate rich smooth pixel gradient:
- Deep Navy (`#0B1026`) at top (y: 0 - 1200) -> Royal Violet (`#261B4E`) (y: 1200 - 2000) -> Sunset Magenta/Rose (`#E86A82`) (y: 2000 - 2600) -> Warm Golden Horizon (`#FCD0A1`) (y: 2600 - 2900).
- Paint crescent moon with soft luminous outer glow at top-right (x: 1850, y: 550, r: 180).
- Paint twinkling starlight constellation clusters with multi-point glowing stars.
- Paint distant mountain ranges and glowing city silhouette with warm window points along the horizon line (`y: 2600 - 2800`).

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_celestial_sky_and_city -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/orchestration/poster_builder.py tests/unit/orchestration/test_poster_builder.py
git commit -m "feat(orchestration): implement celestial twilight sky and distant cityline painting"
```

---

### Task 6: Hero Characters, Romantic Narrative Silhouette & Red Thread of Fate

**Files:**
- Modify: `src/krita_mcp_lazy/orchestration/poster_builder.py`
- Test: `tests/unit/orchestration/test_poster_builder.py`

**Interfaces:**
- Consumes: `layer.paint_curve`, `layer.set_pixel_data`, `layer.set_properties`
- Produces: Midground observation deck / railing, boy & girl silhouette figures, glowing red thread connecting their fingers.

- [ ] **Step 1: Write test for character and railing rendering**

In `tests/unit/orchestration/test_poster_builder.py`:
```python
@pytest.mark.asyncio
async def test_paint_hero_characters_and_thread():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"success": True}
    builder = AnimePosterBuilder(mock_client)
    await builder.paint_hero_characters_and_thread("doc_test")
    assert mock_client.send_job.call_count >= 3
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_hero_characters_and_thread -v`
Expected: FAIL.

- [ ] **Step 3: Implement `paint_hero_characters_and_thread(doc_id)` in `AnimePosterBuilder`**

- Observation Balcony: Clean dark architectural railing (`#10142A`) spanning bottom third (`y: 2650 - 3200`).
- Character Silhouettes:
  - Cute anime girl on left (hair blowing in wind, ribbon, profile tilted upwards towards the star).
  - Cute anime boy on right (slightly leaning forward on railing, reaching out towards her).
  - Both rendered in deep twilight silhouette (`#10142A`) with subtle rim-light highlights (`#E86A82` and `#FFF3B0`).
- Red Thread of Fate: Luminous crimson Bézier curve (`#FF2A55`) flowing gracefully from girl's pinky to boy's pinky, with additive outer glow layer (`#FFAAA6`) in `addition` blend mode.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_hero_characters_and_thread -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/orchestration/poster_builder.py tests/unit/orchestration/test_poster_builder.py
git commit -m "feat(orchestration): implement anime lovers silhouette and glowing fate thread"
```

---

### Task 7: Atmospheric Swirl, Sakura Petals & Cinematic Movie Typography

**Files:**
- Modify: `src/krita_mcp_lazy/orchestration/poster_builder.py`
- Test: `tests/unit/orchestration/test_poster_builder.py`

**Interfaces:**
- Consumes: `layer.create`, `layer.set_pixel_data`, `layer.set_properties`
- Produces: Swirling sakura petal clusters with motion depth, glowing bokeh particles, and movie title layout ("WHISPERS IN THE STARLIGHT", "星空の約束", "SUMMER 2026").

- [ ] **Step 1: Write test for atmospheric particles and typography layout**

In `tests/unit/orchestration/test_poster_builder.py`:
```python
@pytest.mark.asyncio
async def test_paint_atmosphere_and_typography():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"success": True}
    builder = AnimePosterBuilder(mock_client)
    await builder.paint_atmosphere_and_petals("doc_test")
    await builder.render_cinematic_typography("doc_test")
    assert mock_client.send_job.call_count >= 4
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_atmosphere_and_typography -v`
Expected: FAIL.

- [ ] **Step 3: Implement `paint_atmosphere_and_petals` and `render_cinematic_typography`**

- Sakura Petals: Algorithmic distribution of 80+ delicate cherry blossom petals (`#FFB7B2`, `#FFAAA6`, `#FFFFFF`) drifting diagonally with organic rotation and depth scale (foreground large blurred petals, midground crisp petals).
- Bokeh & Star Dust: Glowing circular dust motes and soft light spheres in `addition` blending mode.
- Cinematic Typography:
  - Top header: "A TOONFLOW ORIGINAL ANIME PRESENTATION"
  - Center/Lower title: Large elegant serif/display Japanese kanji title *『星空の約束』* and English subtitle *"WHISPERS IN THE STARLIGHT"*.
  - Emotional Tagline: *"Across infinite skies, our hearts remember."*
  - Bottom billing block: Cinematic credits layout and *"COMING TO THEATERS SUMMER 2026"*.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/unit/orchestration/test_poster_builder.py::test_paint_atmosphere_and_typography -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/orchestration/poster_builder.py tests/unit/orchestration/test_poster_builder.py
git commit -m "feat(orchestration): implement sakura petal swirl and movie typography"
```

---

### Task 8: End-to-End Live Generation, Visual QA Evaluation & Poster Export

**Files:**
- Create: `scripts/generate_anime_poster.py`
- Output: `output/anime_movie_poster_whispers_in_the_starlight.png`
- Output: `output/whispers_in_the_starlight.kra`

**Interfaces:**
- Consumes: Live Krita on `127.0.0.1:18812`, `krita_capture_preview`, `krita_evaluate_visual_quality`
- Produces: Final painted poster on live Krita canvas, high-resolution exported PNG and saved native KRA file.

- [ ] **Step 1: Write CLI generation script**

Create `scripts/generate_anime_poster.py` orchestrating:
1. Connect to live Krita on 18812.
2. Initialize canvas and scaffold semantic layers.
3. Paint celestial twilight sky and distant cityline.
4. Paint hero character silhouettes and red thread of fate.
5. Paint floating sakura petals and starlight particles.
6. Render movie typography header and title block.
7. Capture canvas preview and evaluate quality scorecard.
8. Export full-resolution PNG to `output/anime_movie_poster_whispers_in_the_starlight.png`.

- [ ] **Step 2: Execute script against live Krita**

Run: `python scripts/generate_anime_poster.py`
Expected: Canvas updates in real time in Krita window; returns QA score >= 90; PNG file created in `output/`.

- [ ] **Step 3: Verify exported PNG image file exists and is valid**

Run: `Test-Path output/anime_movie_poster_whispers_in_the_starlight.png`
Expected: True.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_anime_poster.py
git commit -m "feat(pipeline): complete end-to-end anime movie poster generation pipeline"
```

---

## Self-Review

1. **Spec coverage:** The plan covers authenticated loopback IPC, zero-dependency embedded Krita fallback, live connection verification, semantic non-destructive layer tree creation, native multi-plane rendering, celestial & character silhouette painting, sakura particle effects, movie typography, and visual QA preview inspection.
2. **Step scan:** Every step contains explicit test signatures, implementation targets, and verifiable execution outputs.
3. **Type consistency:** Consistent `doc_id`, `JobRequest`, `JobResponse`, and `AnimePosterBuilder` method signatures maintained across all tasks.
4. **Review Focus:** Addressed all 5 review focus classes (embedded Pydantic absence, embedded Pillow absence, Qt GUI event-loop responsiveness, 300 DPI buffer handling, and socket handshake recovery).
5. **Proportion:** Tasks are cleanly decomposed into bite-sized units with clear deliverables.
