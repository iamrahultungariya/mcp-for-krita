# Spec: krita-MCP-lazy (ToonFlow Art Engine)

## 1. Mission and High-Level Objectives
Build an independent, professional AI Art Production Engine and Model Context Protocol (MCP) server named **`krita-MCP-lazy`** that enables AI orchestrators (like ToonFlow) to operate Krita as a professional digital art studio.

- **Primary Artwork Application**: Krita (via native Python plugin and MCP server).
- **Central Artistic Orchestrator**: ToonFlow (governs artistic decision making, composition, anatomy, style, and review).
- **Primary 2D Animation Application**: Tahoma2D (Krita acts as raster frame/asset creator, not primary puppet/scene animator).
- **Core Principle**: MCP handles reliable, deterministic, authenticated tool execution; ToonFlow handles artistic intelligence and visual direction.

## 2. Non-Negotiable System Requirements
1. **Independent Clean-Room Implementation**: No code inherited or forked from `nanayax3/krita-mcp`. Original protocol, plugin, server, and tests.
2. **Modular Architecture**: Discrete modules for core, transport, plugin bridge, documents, layers, painting, art planning, characters, environments, assets, visual QA, animation, Tahoma2D interop, and telemetry.
3. **No Subagents**: Autonomous sequential execution without subagent delegation overhead.
4. **Execution Modes**: Quick, Deep, and Production modes preserved.
5. **Local-First & Loopback**: All IPC restricted to localhost (127.0.0.1) with session tokens. No public exposure.
6. **Zero Arbitrary Execution**: No arbitrary Python `eval()` or unauthenticated shell/filesystem execution via tools.
7. **Native Painting Priority**: Use native Krita brushes and API strokes; synthetic direct pixel rendering is strictly an internal utility fallback, never the primary painting engine.
8. **Editable Source Preservation**: Krita native `.kra` documents with full non-destructive layer trees, masks, and metadata must be preserved.
9. **Visual Verification Mandatory**: Every critical painting/layer step captures canvas state and inspects actual visual output.
10. **Reversible Destructive Operations**: Checkpoints and rollback support for canvas/layer mutations.
11. **Observable Telemetry**: Real wall-clock timing, memory footprint, and CPU metrics. Zero fake or estimated timings.
12. **Structured Errors & Backpressure**: Bounded queues, job IDs, cancellation, and typed error responses.

## 3. System Architecture & Logical Modules
```
+--------------------------------------------------------------------+
|                   ToonFlow AI Orchestrator                         |
|            (Quick / Deep / Production Art Director)                |
+---------------------------------+----------------------------------+
                                  | MCP Protocol (stdio / SSE)
                                  v
+--------------------------------------------------------------------+
|                 Krita MCP Server (krita-MCP-lazy)                  |
|  - FastMCP Tool Registry                                           |
|  - Input Validation & Typed Schemas                                |
|  - Job Manager & Deadlines                                         |
|  - Telemetry & Real Timing                                         |
+---------------------------------+----------------------------------+
                                  | Authenticated Loopback IPC
                                  | (Unix Domain Socket / TCP + Token)
                                  v
+--------------------------------------------------------------------+
|                Krita Native Python Plugin (Extension)              |
|  - Plugin Entry Point & Desktop Registration                       |
|  - Main-Thread Dispatcher (QTimer / PyQt event loop safe)          |
|  - Status Docker (Real-time connection & job UI)                  |
|  - Document & View Observers                                       |
+---------------------------------+----------------------------------+
                                  | Native PyQt5/PyQt6 Krita API
                                  v
+--------------------------------------------------------------------+
|                      Krita Desktop Application                     |
|  - KisDocument, KisView, KisNode, KisPaintDevice                   |
|  - Brush Engine & KisPaintOpPreset                                 |
|  - Layers, Transparency Masks, Filter Masks, Transform Masks       |
|  - Animation Cache & Onion Skin                                    |
|  - OCIO / ICC Color Management                                     |
+--------------------------------------------------------------------+
```

### Module Responsibilities:
- `core`: Configuration, shared schemas, error codes, security policies, token management.
- `transport`: Authenticated loopback IPC (client/server), message serialization, bounded queues, heartbeats.
- `plugin_bridge`: Krita Python extension (`krita_mcp_bridge`), main-thread task runner, status docker, document lifecycle hooks.
- `document`: Canvas creation, open/save/duplicate `.kra`, dimensions, DPI, color models (RGBA, CMYK), bit depths (8/16/32-bit), ICC/OCIO profiles.
- `layers`: Hierarchical tree management, grouping, opacity, blending modes, transparency masks, filter masks, clipping, alpha inheritance.
- `painting`: Brush preset discovery, size/opacity/flow/color configuration, vector stroke generation, smoothing, pressure simulation, native stroke execution.
- `art_planning`: Rule of thirds, composition grid, color harmonizers, lighting schemes, style specs, camera framing plans.
- `character`: Turnaround specification (front, 3/4, side, back), proportion matrices, anatomical guides, facial feature anchor points, expression/viseme sheets.
- `environment`: Perspective grid generators (1-point, 2-point, 3-point), depth planes (FG/MG/BG), architectural and natural props, lighting atmosphere.
- `assets`: Reusable prop catalog, transparent PNG asset slicing, pivot metadata export, texture library.
- `visual_qa`: Render preview extraction, image diffing, anatomy/perspective checks, visual scorecard evaluation (target 85/100), automated correction loop.
- `animation`: Keyframe creation, blank/duplicate frame insertion, frame timing, onion skinning, PNG sequence export, memory caching guard (< 200 MiB/s budget).
- `interop_tahoma2d`: Multi-layer PNG asset packaging, pivot coordinates, alignment checks, Tahoma2D scene project generator & round-trip validator.
- `telemetry`: Monotonic wall-clock timer, RAM/VRAM resource monitors, step-by-step trace logger.

## 4. Phase Breakdown (Phases 1 to 12)
- **Phase 1: Foundation & Application Communication**
  - FastMCP server setup, typed tools, loopback IPC with token auth, Krita extension + status docker, main thread queue dispatcher.
- **Phase 2: Document & Canvas Intelligence**
  - Document CRUD, canvas bounds, rotation, resize, cropping, color profile (ICC/OCIO), bit depth, unsaved state checking.
- **Phase 3: Advanced Layer Intelligence**
  - Layer CRUD, tree hierarchy, grouping, alpha inheritance, clipping, masks (transparency, filter, selection, transform), semantic naming.
- **Phase 4: Native Drawing & Painting Engine**
  - Brush discovery, preset inspection, stroke coordinates, pressure/speed profiles, stroke preview and native painting execution.
- **Phase 5: Art Direction & Composition Engine**
  - Visual production specification generator: composition, camera, lighting, palette, depth planes, quality criteria.
- **Phase 6: Professional Character Production**
  - Character turnaround sheets, proportion consistency, anatomical structure, facial expression & viseme system, reference fidelity.
- **Phase 7: Environment & Prop Production**
  - Perspective environments, atmospheric depth, props & kit modular assets, PBR-like material rendering (wood, metal, fabric, glass, stone, water).
- **Phase 8: Visual Intelligence & Quality Control**
  - Viewport/canvas capture, defect detection (anatomy, clipping, lines, lighting), 85/100 scorecard calculation, surgical checkpoint rollback.
- **Phase 9: Animation & Frame Production**
  - Keyframe raster drawing, breakdown frames, timing, onion skin, memory-safe caching, PNG sequence export.
- **Phase 10: Tahoma2D Interoperability**
  - Cutout & raster asset export with pivot metadata, Tahoma2D scene structure generation, round-trip import/export validation.
- **Phase 11: Telemetry & Performance Monitoring**
  - Real wall-clock timing, resource consumption (RAM, CPU), queue latency tracking, reproducible benchmark reporter.
- **Phase 12: Production Release & Dogfooding**
  - Execution of 60 rigorous dogfooding challenges across all 8 disciplines, full scorecard validation, documentation, deployment scripts.

## 5. Dogfooding Suite: 8 Disciplines & 60 Benchmarks
1. **Character Illustration (Tests 01-10)**: Hero character, turnaround (4 views), expression sheet (6 emotions), visemes/mouth shapes, hair locks, hands/fingers, clothing textures, dynamic pose, lighting variation, dual-character interaction.
2. **Environment & Background (Tests 11-18)**: Horror interior, natural forest, cyberpunk rain urban, interior room design, multi-room basement, 2-point perspective building exterior, night multi-light scene, daylight atmospheric depth.
3. **Props & Material Studies (Tests 19-26)**: Furniture (chair/table/bed), fabric/curtains folds, natural assets (rocks/plants/water), mechanical props, realistic wood grain, glass/reflection, stone/cracks, water transparency.
4. **Drawing & Painting Intelligence (Tests 27-34)**: Brush stroke comparisons (pencil vs ink vs airbrush vs texture), curve rendering across presets, line art cleanup, skin multi-layer shading, hair highlights, cloth rendering, smooth gradient blending, complex mask shading.
5. **Advanced Visual Challenges (Tests 35-42)**: Cinematic lighting, 3-point perspective city, visual FX (glow/sparks/smoke), atmospheric fog, golden hour sunset, underwater caustics, rim light drama, high-contrast chiaroscuro.
6. **Document & Layer Stress Tests (Tests 43-48)**: 100-layer complex artwork, deeply nested groups/masks, 4K canvas stress, multi-document concurrent handling, KRA save-close-reopen fidelity, 50-asset batch slice export.
7. **Animation & Production Tests (Tests 49-54)**: 5s hand-drawn idle loop, walk-cycle key poses & in-betweens, facial expression morph, 10s frame sequence, PNG sequence render verification, complete layered character Tahoma2D export.
8. **Visual Correction Challenges (Tests 55-60)**: Anatomical error auto-correction, perspective distortion repair, missing finger reconstruction, layer order auto-fix, color inconsistency harmonization, interrupted job checkpoint rollback.

## 6. Scorecard & Acceptance Criteria
- **Anatomy & Proportions**: 15%
- **Line Quality & Drawing**: 15%
- **Composition & Perspective**: 15%
- **Lighting & Shading**: 15%
- **Color & Materials**: 10%
- **Reference Fidelity**: 15%
- **Detail & Finish**: 10%
- **Layer & Editability Quality**: 5%
- **Minimum Target Artistic Score**: 85 / 100.
- **Technical Acceptance**: 100% communication reliability, 100% document save/reopen fidelity, zero unhandled crashes, real wall-clock timing.
