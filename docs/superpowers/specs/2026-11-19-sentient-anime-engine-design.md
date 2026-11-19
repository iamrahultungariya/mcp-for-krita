# Design Specification: Sentient Krita AI Artist Engine & Anime Character Pipeline

**Document ID**: `SPEC-SENTIENT-KRITA-2026-11-19`  
**Status**: APPROVED  
**Date**: 2026-11-19  
**Target Host**: Krita 5.x + FastMCP Server (Loopback IPC `127.0.0.1:18812`)  
**Scope**: Phase 1 (Sentient Oracle, Real Live Drawing, Native Color Grading) & Phase 2 (Autonomous Anime Character Engine, 12-Frame Stride Rig, Master 10s Animation)

---

## 1. Executive Summary & Problem Diagnosis

In previous iterations, the animation and drawing pipeline suffered from critical architectural shortcomings:
1. **Stick-Figure Rendering Regression**: `run_cycle_engine.py` generated characters using primitive OpenCV `cv2.line` and `cv2.circle` calls, culminating in a 36px line for hair that produced an unesthetic brown cylinder on the character's head.
2. **Fake Live Drawing**: `canvas_tablet_driver.py`'s `execute_live_stroke` was a no-op returning `{"mode": "live_krita", "success": True}` without posting events to Krita's canvas or painting pixels.
3. **Color Inversion / Washed Out Palette**: Strokes were sent in RGBA bytes rather than Krita's native little-endian BGRA channel layout, causing color degradation.
4. **Missing In-App Color Grading**: Color grading existed only as an OpenCV post-process on exported MP4s, leaving Krita `.kra` documents flat and unadjusted.
5. **Passive Environment Blindness**: The system required manual user prompting ("Krita is open, file is open") because no autonomous state oracle actively monitored connection or active document metadata.
6. **Bypassed Tool Calling**: Instead of orchestrating the newly added FastMCP tools (`krita_live_paint_anime_character`, `krita_export_reusable_rig`, `krita_paint_stroke`), the execution fell back to an ad-hoc monolithic OpenCV script.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Autonomous Bridge State Oracle**: Auto-probe port 18812 and query `app.activeDocument()` immediately on every invocation, extracting canvas dimensions, DPI, active layers, and zoom level without asking the user.
- **Real In-Canvas Progressive Live Drawing**: Implement real-time progressive stroke and tile push onto `KisPaintLayer` in native BGRA format, displaying visible stroke updates on the Krita viewport.
- **Native Krita In-App Color Grading**: Generate native adjustment/filter layers (Curves, Color Balance, Cross-Channel, Bloom/Glow) directly inside the `.kra` layer hierarchy.
- **Artistic Anime Anatomy & Hair Clustering Engine**: Replace OpenCV primitive stick drawing with an authentic anime character generator adhering to studio anime rules (head-to-body 1:7.5, geometric tapering hair ribbons, 3-plane facial anatomy, dual-highlight eyes, crisp cel-shadow trapping with `inherit_alpha=True`).
- **12-Frame Athletic Running Rig**: Generate a 12-frame 2-step looping stride cycle with organic squash-and-stretch, momentum-delayed ponytail dynamics, parabolic sweat droplet physics, and stadium parallax.
- **10-Second Master Video Deliverable**: Render a fluid 240-frame, 24 FPS, high-bitrate MP4 with cinematic color grading and speedline VFX.

### Non-Goals
- Replacing Krita's core C++ engine.
- Requiring cloud GPU clusters for basic 2D drawing (must run locally on CPU/local GPU).

### Anti-Goals
- Any fallback to OpenCV `cv2.line` / `cv2.circle` stick figures.
- Silent headless fallback that hides Krita connection status.
- Flat, unlayered video generation that skips Krita canvas layer persistence.

---

## 3. Reference Image Breakdown (Anime Visual Standards)
- **Reference 1 (Current Defect)**: Stickman with cylindrical hair bar, flat green/blue background. (Negative anchor).
- **Reference 2 (Streetwear Character)**: Full-body anime anatomy, crisp line weight variations, clothing folds at joints, 2-tone cel shadows, accurate footwear design.
- **Reference 3 (Portrait Lookdev)**: Multi-strand layered hair with tapering locks, golden-hour rim lighting ("angel ring"), detailed anime eyes with pupil depth and double specular glints, nose bridge shadow.
- **Reference 4 (Dynamic Action)**: Expressive face, clean chin angle, volumetric twin buns, multi-element jacket with zipper/strap details, bold comic ink lines.
- **Reference 5 (Protagonist Grid)**: Standardized facial proportions (eye line at mid-lower third, mouth-to-chin spacing, sharp jaw, clean sclera).

---

## 4. Architectural Approach: Tool-Calling Driven AI Artist

```
┌────────────────────────────────────────────────────────┐
│                   AI ARTIST AGENT                      │
│   (Art Planning, Anatomy Grammar, Tool Orchestration)  │
└───────────────────────────┬────────────────────────────┘
                            │ Tool Calls via FastMCP
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FASTMCP SERVER                       │
│  - krita_auto_sense_context                            │
│  - krita_scaffold_cel_stack                            │
│  - krita_live_draw_stroke                              │
│  - krita_apply_adjustment_layers                       │
│  - krita_build_anime_character_rig                     │
│  - krita_generate_running_animation                    │
└───────────────────────────┬────────────────────────────┘
                            │ Async IPC (127.0.0.1:18812)
                            ▼
┌────────────────────────────────────────────────────────┐
│             KRITA EMBEDDED PYTHON BRIDGE               │
│  - BridgeStateOracle & Handshake                       │
│  - KisPaintLayer Progressive BGRA Tile Driver          │
│  - KisAdjustmentFilter Generator                       │
│  - Viewport Canvas Redraw Trigger                      │
└────────────────────────────────────────────────────────┘
```

---

## 5. Phase Breakdown

### Phase 1: Sentient Foundation, Live Drawing & In-App Grading
1. **`BridgeStateOracle`**: Active socket probe, port 18812 handshake, `document.inspect_active` native handler returning open canvas details.
2. **`RealLiveCanvasDriver`**: Real progressive stroke renderer writing BGRA chunks to `KisPaintLayer.setPixelData()` with immediate `doc.refreshProjection()`.
3. **`InAppColorGrading`**: Native Krita adjustment layer generator applying Color Balance, Curves, and Screen-blend Atmospheric Glow.

### Phase 2: Autonomous Anime Character Engine, Rig & 10s Animation
1. **`AnimeCharacterArtEngine`**: High-fidelity vector/raster character generator replacing stick figures with real anime anatomy (eyes, hair clusters, athletic wear, folds).
2. **`ModularAthleticStrideRig`**: 12-frame looping kinematic poses with secondary hair/cloth physics and sweat particle emitter.
3. **`StadiumParallaxBuilder`**: Multi-plane parallax background (morning sky sunburst, concrete bleachers with turf, polyurethane running track).
4. **`MasterVideoRenderer`**: 240-frame, 24 FPS 10-second master MP4 video generation with speedlines and sound stage composition.
