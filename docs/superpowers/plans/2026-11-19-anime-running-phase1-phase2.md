# Anime Running Animation (Phase 1 & 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 1 (Cinematic Stadium Environment & Parallax Scaffolding in Krita) and Phase 2 (Vibrant Athletic Character Redesign & 12-Frame Cel Stride Cycle) with rich, saturated cinematic colors and warm golden-hour rim lighting.

**Architecture:** A modular Python pipeline interacting with Krita's live loopback IPC (`127.0.0.1:18812`) to scaffold 4K multi-plane background layers into `running.kra` (`doc_4`), render vibrant high-contrast stadium art, and generate an authentic 12-frame anime running cycle with rich cel shading, deep shadows, and sunlit rim lighting.

**Tech Stack:** Python 3.14, Krita 5.x IPC Bridge, OpenCV, NumPy, Pillow, FastMCP.

**Spec:** [docs/superpowers/specs/2026-11-19-anime-running-animation-design.md](file:///c:/Users/Rahul/OneDrive/Desktop/Krita%20MCP/docs/superpowers/specs/2026-11-19-anime-running-animation-design.md)

## Global Constraints
- Target Krita document: `doc_4` (`running.kra`, $3840 \times 2160\text{ px}$).
- Color Grading & Palette: High-contrast, vibrant, cinematic. Avoid desaturated or washed-out tones; employ deep blacks for inking, rich terracotta reds for the track, cobalt navy for running gear, warm peach skin tones, and bright golden sunlight highlights.
- Zero White Halo: Morphological under-trapping $\ge 2\text{ px}$ on all flat color boundaries.
- Alpha Inheritance: Native `inheritAlpha=True` on all shading and highlight layers.
- Frame Count: Exactly 12 key stride poses for the 2-step loop cycle.

## Review Focus
1. Canvas Layer Sync: Verify that `doc_4` contains properly nested group layers and paint layers with correct blending modes.
2. Color Saturation: Verify that track and character colors have high chroma ($S > 0.45$ in HSV space) to avoid faded aesthetic.
3. Alpha Clipping: Verify that shadow layers do not bleed beyond the character silhouettes.
4. G-Pen Line Quality: Verify inking lines retain crisp tapered edges.
5. Verification Artifacts: Output high-resolution visual previews to `output/` for user review.

---

### Task 1: Cinematic Stadium Multi-Plane Parallax Environment Generator (Phase 1)

**Files:**
- Create: `src/krita_mcp_lazy/animation/cinematic_stadium_builder.py`
- Create: `tests/unit/animation/test_stadium_builder.py`

- [ ] **Step 1: Write unit tests for cinematic stadium environment generator**
  Create test verifying generation of:
  - Sky layer ($3840 \times 2160$) with vibrant morning gradient and sunburst flare.
  - Bleachers & green turf infield layer with depth perspective.
  - Polyurethane track layer with deep terracotta red and crisp white running lanes.
  - High saturation verification check.

- [ ] **Step 2: Run test to confirm failure**
  ```bash
  pytest tests/unit/animation/test_stadium_builder.py
  ```

- [ ] **Step 3: Implement `cinematic_stadium_builder.py`**
  Implement procedural and high-fidelity rendering of:
  - `generate_sky_plane(width, height)`: Deep cerulean to cyan gradient with golden sun bloom.
  - `generate_bleachers_plane(width, height)`: Concrete stadium grandstands with vivid green infield.
  - `generate_track_plane(width, height)`: Saturated red (#B3261E / #D32F2F) running track with curved white lane lines.
  - `scaffold_stadium_in_krita(client, doc_id)`: Push layers to `running.kra` with BGRA pixel tiles.

- [ ] **Step 4: Run test to confirm pass**
  ```bash
  pytest tests/unit/animation/test_stadium_builder.py
  ```

- [ ] **Step 5: Execute stadium scaffolding on live Krita `doc_4`**
  Connect to live Krita IPC and inject the stadium layers into `running.kra`.

---

### Task 2: Athletic Character Redesign & Cinematic Palette Engine (Phase 2A)

**Files:**
- Create: `src/krita_mcp_lazy/animation/athletic_character_rig.py`
- Create: `tests/unit/animation/test_athletic_character.py`

- [ ] **Step 1: Write unit tests for athletic character metadata and color profile**
  Verify:
  - Palette definition: Cobalt Navy (#1A365D), Athletic White (#FFFFFF), Warm Peach Skin (#FAD2B8), Rich Brunette Hair (#4A2810), Golden Sun Rim (#FFE082), Deep Cel Shadow (#1E152A).
  - Costume geometry: Tank top, shorts, sweatband, wristband.

- [ ] **Step 2: Run test to confirm failure**
  ```bash
  pytest tests/unit/animation/test_athletic_character.py
  ```

- [ ] **Step 3: Implement `athletic_character_rig.py`**
  Implement:
  - Athletic runner anatomy and costume generator.
  - High-chroma color palette with warm golden-hour lighting profiles.
  - Integration with `CharacterRigMetadata` and manifest export.

- [ ] **Step 4: Run test to confirm pass**
  ```bash
  pytest tests/unit/animation/test_athletic_character.py
  ```

---

### Task 3: 12-Frame Studio Cel Stride Loop Generator & Krita Live Sync (Phase 2B)

**Files:**
- Create: `src/krita_mcp_lazy/animation/run_cycle_engine.py`
- Create: `tests/unit/animation/test_run_cycle_engine.py`

- [ ] **Step 1: Write unit tests for 12-frame stride cycle generator**
  Verify:
  - 12 sequential frames: Contact 1, Recoil 1, Passing 1, Air 1, Peak 1, Decel 1, Contact 2, Recoil 2, Passing 2, Air 2, Peak 2, Decel 2.
  - Stride displacement, knee angles, and hair bounce vectors.
  - Layer composition: Lineart, Flat, Multiply Shadow, Sun Rim Highlight.

- [ ] **Step 2: Run test to confirm failure**
  ```bash
  pytest tests/unit/animation/test_run_cycle_engine.py
  ```

- [ ] **Step 3: Implement `run_cycle_engine.py`**
  Implement:
  - Mathematical stride kinematics ($0.5\text{s}$ per 2-step stride).
  - Tapered G-Pen inking + 2px under-trapped flats + multiply cel shadows + golden rim lighting.
  - Layer injection into Krita `doc_4` under `Char_Run_Cycle` group.
  - Export composite turnaround preview image to `output/preview_run_cycle.png`.

- [ ] **Step 4: Run test to confirm pass**
  ```bash
  pytest tests/unit/animation/test_run_cycle_engine.py
  ```

- [ ] **Step 5: Execute full Phase 1 & 2 integration script**
  Run pipeline on live Krita canvas `running.kra` and output high-res preview image for user inspection.
