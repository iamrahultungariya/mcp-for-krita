# krita-MCP-lazy — Project Status & Cross-Session Tracker

> **AGENT HANDOFF INSTRUCTION (READ FIRST IN ANY CHAT):**
> If you are an AI agent opening this repository in a new chat session:
> 1. Read this file (`PROJECT_STATUS.md`) and the master plan at `docs/superpowers/plans/2026-11-18-krita-mcp-lazy.md`.
> 2. Check the **Current Active Phase & Next Action** section below.
> 3. Do not ask for redundant clarifications or change the architecture: proceed directly with the first uncompleted task using TDD (Write test -> Verify Fail -> Implement -> Verify Pass -> Commit).
> 4. Keep subagents disabled (Native sequential execution).

---

## Current State at a Glance

- **Project Name:** `krita-MCP-lazy` (ToonFlow Art Engine)
- **Active Phase:** **Phase 1: Foundation & Application Communication**
- **Next Task to Execute:** **Task 3: Native Krita Python Extension Plugin & Main-Thread Queue Dispatcher (`plugins/krita_mcp_bridge/`)**
- **Architecture Spec:** [`docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md`](docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md)
- **Implementation Plan:** [`docs/superpowers/plans/2026-11-18-krita-mcp-lazy.md`](docs/superpowers/plans/2026-11-18-krita-mcp-lazy.md)

---

## Phase & Task Progress Tracker

### [ ] Phase 1: Foundation & Application Communication (Status: IN PROGRESS)
- [x] **Task 1:** Core Configuration, Schemas, Security & Error Types (`src/krita_mcp_lazy/core/`)
- [x] **Task 2:** Authenticated Loopback IPC Transport (`src/krita_mcp_lazy/transport/`)
- [ ] **Task 3:** Native Krita Python Extension Plugin & Main-Thread Queue Dispatcher (`plugins/krita_mcp_bridge/`)
- [ ] **Task 4:** FastMCP Server Integration & Core Tool Registration (`src/krita_mcp_lazy/server/`)

### [ ] Phase 2: Document & Canvas Intelligence (Status: PENDING)
- [ ] **Task 5:** Document Engine (CRUD, Save/Open KRA, Color Profile & Bit Depth) (`src/krita_mcp_lazy/document/`)
- [ ] **Task 6:** Canvas Engine (Resize, Crop, Rotation, Bounds & Pixel Sampling) (`src/krita_mcp_lazy/document/canvas.py`)

### [ ] Phase 3: Advanced Layer Intelligence (Status: PENDING)
- [ ] **Task 7:** Layer Hierarchy & Mask Engine (Tree management, groups, opacity, blending) (`src/krita_mcp_lazy/layers/`)
- [ ] **Task 8:** Advanced Masking, Clipping & Alpha Inheritance (`src/krita_mcp_lazy/layers/masks.py`)
- [ ] **Task 9:** Semantic Layer Organization & Custom Hierarchies (`src/krita_mcp_lazy/layers/semantic.py`)

### [ ] Phase 4: Native Drawing & Painting Engine (Status: PENDING)
- [ ] **Task 10:** Brush Preset Discovery, Inspection & Parameter Configuration (`src/krita_mcp_lazy/painting/brush_service.py`)
- [ ] **Task 11:** Native Stroke Generation, Pressure Simulation & Vector Path Automation (`src/krita_mcp_lazy/painting/stroke_engine.py`)

### [ ] Phase 5: Art Direction & Composition Engine (Status: PENDING)
- [ ] **Task 12:** Visual Production Specification Generator (`src/krita_mcp_lazy/art_planning/`)

### [ ] Phase 6: Professional Character Production (Status: PENDING)
- [ ] **Task 13:** Character Turnaround & Anatomical Construction Engine (`src/krita_mcp_lazy/character/turnaround.py`)
- [ ] **Task 14:** Facial System, Expressions & Visemes Engine (`src/krita_mcp_lazy/character/expressions.py`)

### [ ] Phase 7: Environment & Prop Production (Status: PENDING)
- [ ] **Task 15:** Perspective Grids & Multi-Plane Environment Engine (`src/krita_mcp_lazy/environment/`)
- [ ] **Task 16:** Modular Prop Generator & Material Shading Engine (`src/krita_mcp_lazy/assets/`)

### [ ] Phase 8: Visual Intelligence & Quality Control (Status: PENDING)
- [ ] **Task 17:** Canvas Preview Capture & Visual Region Extraction (`src/krita_mcp_lazy/visual_qa/capture.py`)
- [ ] **Task 18:** Quality Control Scorecard Evaluator & Surgical Rollback Engine (`src/krita_mcp_lazy/visual_qa/scorecard.py`)

### [ ] Phase 9: Animation & Frame Production (Status: PENDING)
- [ ] **Task 19:** Raster Keyframe & Timing Engine with Memory Cache Guard (`src/krita_mcp_lazy/animation/keyframe_service.py`)
- [ ] **Task 20:** Frame Sequence Export & Validation Engine (`src/krita_mcp_lazy/animation/exporter.py`)

### [ ] Phase 10: Tahoma2D Interoperability (Status: PENDING)
- [ ] **Task 21:** Multi-Layer Asset Packaging & Pivot Metadata Exporter (`src/krita_mcp_lazy/interop_tahoma2d/packager.py`)
- [ ] **Task 22:** Tahoma2D Scene Project Generator & Round-Trip Validator (`src/krita_mcp_lazy/interop_tahoma2d/scene_builder.py`)

### [ ] Phase 11: Telemetry & Performance Monitoring (Status: PENDING)
- [ ] **Task 23:** Monotonic Wall-Clock Telemetry, Memory & Operation Tracer (`src/krita_mcp_lazy/telemetry/`)

### [ ] Phase 12: Production Release & Dogfooding Suite (Status: PENDING)
- [ ] **Task 24:** 60 Dogfooding Challenges Runner & Production Benchmark Suite (`src/krita_mcp_lazy/dogfooding/`)

---

## Krita Runtime FAQ

### Q: Kya mujhe coding / testing karte waqt Krita open rakhna padega?
**Short Answer: Shuru ke phases aur unit tests ke liye Krita open rakhne ki BILKUL zaroorat nahi hai.**

- **Development & Unit Tests (Tasks 1-24):** All unit tests use headless mocks (`AsyncMock`, mocked socket protocol, synthetic Krita API fixtures). Aapka poora test suite bina Krita open kiye super-fast chalega.
- **Live Krita Testing (When doing manual end-to-end verification):** Sirf tab Krita open karna hai jab aapko live canvas par strokes bante dekhne ho ya Krita plugin docker ka visual test karna ho.
