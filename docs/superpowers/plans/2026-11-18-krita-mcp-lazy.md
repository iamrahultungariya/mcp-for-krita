# krita-MCP-lazy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `krita-MCP-lazy`, an independent, professional AI Art Production Engine and Model Context Protocol (MCP) server that empowers AI orchestrators (like ToonFlow) to operate Krita as a professional digital art studio.

**Architecture:** A two-tier clean-room architecture comprising a FastMCP server and a native Krita Python plugin extension. The FastMCP server handles typed tool contracts, validation, job queues, and telemetry, communicating with the Krita native extension over an authenticated loopback IPC transport. The Krita extension runs tasks safely within Krita's main Qt event loop, providing native painting, document management, semantic layer structures, visual inspection, animation sequencing, and Tahoma2D asset handoff.

**Tech Stack:** Python 3.10+, FastMCP / MCP SDK, Pydantic v2, PyQt5/PyQt6 (Krita native environment), Pillow, NumPy, Pytest, Pytest-asyncio.

**Spec:** [docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md](file:///c:/Users/Rahul/OneDrive/Desktop/Krita%20MCP/docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md)

## Global Constraints

- Independent clean-room implementation; zero code forked or inherited from `nanayax3/krita-mcp`.
- No subagents in execution; sequential, robust execution with high reliability.
- All IPC communication strictly restricted to loopback (127.0.0.1) with cryptographically random session tokens.
- Never expose arbitrary Python `eval()` or unauthenticated shell/filesystem execution via tools.
- Native Krita brush capabilities prioritized over synthetic direct pixel rendering.
- Preserve full source editability in `.kra` native documents with non-destructive layers, masks, and metadata.
- Visual inspection mandatory on every critical canvas and layer operation.
- Reversible destructive operations via checkpoints and rollback.
- Real wall-clock timing measurement only; no estimated or fabricated telemetry numbers.
- Bounded command queues with backpressure and structured error codes.

## Review Focus

1. **Stale/Invalid Session Tokens:** Client attempts IPC communication with expired or forged tokens; must reject with `AUTH_FAILED` (401) immediately and drop the socket without executing commands.
2. **Krita Main-Thread Deadlocks:** Long-running painting or export commands blocking Krita's GUI thread; must be dispatched via bounded main-thread queues and QTimer pump, yielding control to the Qt event loop.
3. **Out-of-Memory (OOM) during Animation Sequencing:** Large canvas (4K) multi-frame animations consuming gigabytes of RAM; must guard memory consumption against the 200 MiB/s budget and enforce disk-backed caching.
4. **Destructive Canvas Rollback Failure:** Canvas mutation fails midway; checkpoint must cleanly revert layer trees and canvas pixels to the exact pre-operation snapshot without file corruption.
5. **Corrupted KRA Document Reopening:** Modified document fails to reopen or loses layer masks/blending modes; must verify save/reopen round-trip fidelity before confirming success.

---

### Task 1: Core Configuration, Schemas, Security & Error Types

**Files:**
- Create: `pyproject.toml`
- Create: `src/krita_mcp_lazy/core/config.py`
- Create: `src/krita_mcp_lazy/core/errors.py`
- Create: `src/krita_mcp_lazy/core/schemas.py`
- Create: `src/krita_mcp_lazy/core/security.py`
- Test: `tests/unit/core/test_core.py`

**Interfaces:**
- Consumes: None (base foundation).
- Produces: `KritaConfig`, `KritaError`, `ErrorCode`, `AuthTokenManager`, `JobRequest`, `JobResponse`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_core.py
import pytest
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.core.errors import KritaError, ErrorCode
from krita_mcp_lazy.core.security import AuthTokenManager
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus

def test_config_defaults():
    config = KritaConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 18812
    assert config.queue_max_size == 100

def test_auth_token_lifecycle():
    mgr = AuthTokenManager()
    token = mgr.generate_token()
    assert len(token) >= 32
    assert mgr.validate_token(token) is True
    assert mgr.validate_token("invalid_token") is False

def test_job_schemas():
    req = JobRequest(action="document.create", params={"width": 1920, "height": 1080})
    assert req.job_id is not None
    assert req.action == "document.create"
    
    resp = JobResponse(job_id=req.job_id, status=JobStatus.SUCCESS, result={"doc_id": "doc_1"})
    assert resp.status == JobStatus.SUCCESS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_core.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'krita_mcp_lazy'`

- [ ] **Step 3: Implement core modules and project configuration**

Create `pyproject.toml` with `fastmcp`, `pydantic>=2.0`, `pillow`, `numpy`, `pytest`, `pytest-asyncio`.
Implement `KritaConfig` with loopback restrictions (`127.0.0.1`), timeout limits, memory caps.
Implement `ErrorCode` enum (`AUTH_FAILED`, `QUEUE_FULL`, `TIMEOUT`, `KRITA_UNAVAILABLE`, `DOCUMENT_ERROR`, `LAYER_ERROR`, `PAINT_ERROR`).
Implement `AuthTokenManager` using Python's `secrets.token_hex(32)`.
Implement `JobRequest` and `JobResponse` using Pydantic models.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/test_core.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat(core): implement core configuration, security, schemas, and error taxonomy"
```

---

### Task 2: Authenticated Loopback IPC Transport (Server & Client)

**Files:**
- Create: `src/krita_mcp_lazy/transport/protocol.py`
- Create: `src/krita_mcp_lazy/transport/server.py`
- Create: `src/krita_mcp_lazy/transport/client.py`
- Test: `tests/unit/transport/test_ipc_transport.py`

**Interfaces:**
- Consumes: `KritaConfig`, `AuthTokenManager`, `JobRequest`, `JobResponse`, `KritaError`.
- Produces: `AsyncIPCServer`, `AsyncIPCClient`, `send_job()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/transport/test_ipc_transport.py
import pytest
import asyncio
from krita_mcp_lazy.transport.server import AsyncIPCServer
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.core.errors import KritaError, ErrorCode

@pytest.mark.asyncio
async def test_authenticated_ipc_roundtrip():
    token = "test_secret_token_1234567890abcdef"
    
    async def handler(request: JobRequest) -> JobResponse:
        return JobResponse(job_id=request.job_id, status=JobStatus.SUCCESS, result={"echo": request.params})

    server = AsyncIPCServer(host="127.0.0.1", port=19999, valid_token=token, handler=handler)
    await server.start()
    
    try:
        client = AsyncIPCClient(host="127.0.0.1", port=19999, token=token)
        req = JobRequest(action="ping", params={"msg": "hello"})
        res = await client.send_job(req)
        assert res.status == JobStatus.SUCCESS
        assert res.result["echo"]["msg"] == "hello"
        
        # Test invalid token rejection
        bad_client = AsyncIPCClient(host="127.0.0.1", port=19999, token="bad_token")
        with pytest.raises(KritaError) as exc_info:
            await bad_client.send_job(req)
        assert exc_info.value.code == ErrorCode.AUTH_FAILED
    finally:
        await server.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/transport/test_ipc_transport.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing symbols.

- [ ] **Step 3: Implement `protocol.py`, `server.py`, and `client.py`**

Length-prefixed JSON framing (`<4-byte-big-endian-length><json-payload>`).
Socket binding restricted to `127.0.0.1`.
Authentication handshake verifying `Authorization: Bearer <token>` on socket connection.
Bounded read buffer (max 32MB payload) to prevent memory flooding.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/transport/test_ipc_transport.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/transport tests/unit/transport
git commit -m "feat(transport): implement authenticated loopback IPC transport"
```

---

### Task 3: Native Krita Python Extension Plugin & Main-Thread Queue Dispatcher

**Files:**
- Create: `plugins/krita_mcp_bridge/__init__.py`
- Create: `plugins/krita_mcp_bridge/krita_mcp_bridge.desktop`
- Create: `plugins/krita_mcp_bridge/bridge_extension.py`
- Create: `plugins/krita_mcp_bridge/dispatcher.py`
- Create: `plugins/krita_mcp_bridge/status_docker.py`
- Test: `tests/unit/plugin/test_dispatcher.py`

**Interfaces:**
- Consumes: `JobRequest`, `JobResponse`, `JobStatus`.
- Produces: `KritaMainThreadDispatcher`, `BridgeExtension`, `StatusDocker`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/plugin/test_dispatcher.py
import pytest
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus

def test_dispatcher_queue_and_execute():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    
    executed = []
    def sample_action(params):
        executed.append(params["val"])
        return {"processed": True}

    dispatcher.register_handler("test.action", sample_action)
    
    req = JobRequest(action="test.action", params={"val": 42})
    dispatcher.enqueue(req)
    
    assert dispatcher.queue_size() == 1
    # Process tick simulating Qt QTimer tick
    dispatcher.process_pending_jobs()
    
    assert executed == [42]
    assert dispatcher.queue_size() == 0
    resp = dispatcher.get_result(req.job_id)
    assert resp.status == JobStatus.SUCCESS
    assert resp.result["processed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/plugin/test_dispatcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'plugins.krita_mcp_bridge'`

- [ ] **Step 3: Implement plugin extension and dispatcher**

Create `.desktop` file registering `krita_mcp_bridge` in Krita's plugin system.
Implement `KritaMainThreadDispatcher` using a thread-safe `queue.Queue` drained via Qt `QTimer.timeout` (or headless mock tick) to ensure thread-safety with Krita's GUI event loop.
Implement `StatusDocker` (`QDockWidget`) showing server status, active job ID, and elapsed time.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/plugin/test_dispatcher.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/ tests/unit/plugin
git commit -m "feat(plugin): implement native Krita extension and main-thread dispatcher"
```

---

### Task 4: FastMCP Server Integration & Core Tool Registration

**Files:**
- Create: `src/krita_mcp_lazy/server/app.py`
- Create: `src/krita_mcp_lazy/server/tools_system.py`
- Create: `src/krita_mcp_lazy/main.py`
- Test: `tests/unit/server/test_mcp_server.py`

**Interfaces:**
- Consumes: `AsyncIPCClient`, `KritaConfig`, `AuthTokenManager`.
- Produces: `create_mcp_server()`, system status tools (`krita_health_check`, `krita_get_version`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/server/test_mcp_server.py
import pytest
from krita_mcp_lazy.server.app import create_mcp_server

@pytest.mark.asyncio
async def test_mcp_server_initialization():
    server = create_mcp_server()
    assert server is not None
    # Verify tools registered
    tool_names = [tool.name for tool in await server.list_tools()]
    assert "krita_health_check" in tool_names
    assert "krita_get_version" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/server/test_mcp_server.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing tools.

- [ ] **Step 3: Implement MCP server with FastMCP**

Initialize `FastMCP("krita-MCP-lazy")`.
Register system health tools and bridge connectivity checks.
Add CLI entry point in `main.py` supporting stdio transport and token negotiation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/server/test_mcp_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/server src/krita_mcp_lazy/main.py tests/unit/server
git commit -m "feat(server): initialize FastMCP server with system health and capability discovery tools"
```

---

### Task 5: Document Engine (CRUD, Save/Open KRA, Color Profile & Bit Depth)

**Files:**
- Create: `src/krita_mcp_lazy/document/models.py`
- Create: `src/krita_mcp_lazy/document/service.py`
- Create: `src/krita_mcp_lazy/server/tools_document.py`
- Test: `tests/unit/document/test_document_service.py`

**Interfaces:**
- Consumes: `AsyncIPCClient`, `JobRequest`.
- Produces: `DocumentService`, tools: `krita_create_document`, `krita_open_document`, `krita_save_document`, `krita_inspect_document`, `krita_list_documents`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/document/test_document_service.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.document.service import DocumentService
from krita_mcp_lazy.document.models import DocumentSpec, ColorModel, BitDepth

@pytest.mark.asyncio
async def test_document_lifecycle():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "doc_id": "doc_hero_01",
        "width": 3840,
        "height": 2160,
        "color_model": "RGBA",
        "bit_depth": "U8",
        "color_profile": "sRGB-elle-V2-srgbtrc.icc"
    }
    
    svc = DocumentService(client=mock_client)
    spec = DocumentSpec(name="HeroShot", width=3840, height=2160, resolution_dpi=300, color_model=ColorModel.RGBA, bit_depth=BitDepth.U8)
    doc_info = await svc.create_document(spec)
    
    assert doc_info["doc_id"] == "doc_hero_01"
    assert doc_info["width"] == 3840
    mock_client.send_job.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/document/test_document_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Document models, service, and MCP tools**

Define `DocumentSpec`, `ColorModel` (`RGBA`, `CMYK`, `GRAY`), `BitDepth` (`U8`, `U16`, `F32`).
Implement `DocumentService` with actions: `document.create`, `document.open`, `document.save`, `document.close`, `document.inspect`.
Handle native `.kra` file validation and unsaved modifications check.
Register MCP tools in `tools_document.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/document/test_document_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/document src/krita_mcp_lazy/server/tools_document.py tests/unit/document
git commit -m "feat(document): implement document service and MCP document tools"
```

---

### Task 6: Canvas Engine (Resize, Crop, Rotation, Bounds & Pixel Sampling)

**Files:**
- Create: `src/krita_mcp_lazy/document/canvas.py`
- Modify: `src/krita_mcp_lazy/server/tools_document.py`
- Test: `tests/unit/document/test_canvas.py`

**Interfaces:**
- Consumes: `DocumentService`, `AsyncIPCClient`.
- Produces: `CanvasService`, tools: `krita_resize_canvas`, `krita_crop_canvas`, `krita_sample_pixel`, `krita_get_canvas_bounds`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/document/test_canvas.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.document.canvas import CanvasService

@pytest.mark.asyncio
async def test_canvas_resize_and_sample():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"sampled_color": {"r": 255, "g": 128, "b": 0, "a": 255}}
    
    canvas_svc = CanvasService(client=mock_client)
    res = await canvas_svc.sample_pixel(doc_id="doc_1", x=100, y=200)
    assert res["r"] == 255
    assert res["g"] == 128
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/document/test_canvas.py -v`
Expected: FAIL

- [ ] **Step 3: Implement canvas operations**

Support `canvas.resize` (with anchor points), `canvas.crop` (bounding box), `canvas.rotate`, and `canvas.sample_pixel` (returns exact RGBA values from composite or active layer).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/document/test_canvas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/document/canvas.py src/krita_mcp_lazy/server/tools_document.py tests/unit/document/test_canvas.py
git commit -m "feat(canvas): implement canvas geometry and pixel sampling services"
```

---

### Task 7: Layer Hierarchy & Mask Engine (Tree Management, Opacity, Blending)

**Files:**
- Create: `src/krita_mcp_lazy/layers/models.py`
- Create: `src/krita_mcp_lazy/layers/service.py`
- Create: `src/krita_mcp_lazy/server/tools_layers.py`
- Test: `tests/unit/layers/test_layers_service.py`

**Interfaces:**
- Consumes: `AsyncIPCClient`.
- Produces: `LayerService`, `LayerType`, `BlendingMode`, tools: `krita_create_layer`, `krita_delete_layer`, `krita_reorder_layer`, `krita_inspect_layer_tree`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/layers/test_layers_service.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.layers.service import LayerService
from krita_mcp_lazy.layers.models import LayerSpec, LayerType, BlendingMode

@pytest.mark.asyncio
async def test_layer_creation_and_tree_inspection():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "layers": [
            {"id": "grp_character", "name": "Character", "type": "group", "children": [
                {"id": "lyr_lineart", "name": "LineArt", "type": "paint", "opacity": 255, "blending_mode": "normal"},
                {"id": "lyr_color", "name": "Color", "type": "paint", "opacity": 255, "blending_mode": "normal"}
            ]}
        ]
    }
    
    svc = LayerService(client=mock_client)
    tree = await svc.inspect_layer_tree(doc_id="doc_1")
    assert len(tree["layers"]) == 1
    assert tree["layers"][0]["name"] == "Character"
    assert len(tree["layers"][0]["children"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/layers/test_layers_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Layer models and tree management service**

Define `LayerType` (`PAINT`, `GROUP`, `VECTOR`, `FILE`, `CLONE`), `BlendingMode` (`NORMAL`, `MULTIPLY`, `SCREEN`, `OVERLAY`, `COLOR_DODGE`, etc.).
Implement recursive hierarchy queries, layer reordering (above, below, inside group), opacity (0-255 / 0-100%), and visibility toggle.
Register MCP tools in `tools_layers.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/layers/test_layers_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/layers src/krita_mcp_lazy/server/tools_layers.py tests/unit/layers
git commit -m "feat(layers): implement layer hierarchy, grouping, and blending mode services"
```

---

### Task 8: Advanced Masking, Clipping & Alpha Inheritance

**Files:**
- Create: `src/krita_mcp_lazy/layers/masks.py`
- Modify: `src/krita_mcp_lazy/server/tools_layers.py`
- Test: `tests/unit/layers/test_masks.py`

**Interfaces:**
- Consumes: `LayerService`, `AsyncIPCClient`.
- Produces: `MaskService`, `MaskType`, tools: `krita_add_mask`, `krita_set_alpha_inheritance`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/layers/test_masks.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.layers.masks import MaskService, MaskType

@pytest.mark.asyncio
async def test_transparency_and_filter_masks():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"mask_id": "mask_trans_01", "parent_layer_id": "lyr_hair"}
    
    svc = MaskService(client=mock_client)
    res = await svc.add_mask(doc_id="doc_1", layer_id="lyr_hair", mask_type=MaskType.TRANSPARENCY, name="Hair_Shading_Mask")
    assert res["mask_id"] == "mask_trans_01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/layers/test_masks.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Mask service and alpha inheritance**

Support `MaskType`: `TRANSPARENCY`, `FILTER` (blur, color balance, levels), `SELECTION`, and `TRANSFORM`.
Support `set_alpha_inheritance(layer_id, inherit_alpha=True)` for non-destructive clipping layers.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/layers/test_masks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/layers/masks.py src/krita_mcp_lazy/server/tools_layers.py tests/unit/layers/test_masks.py
git commit -m "feat(layers): implement advanced masks (transparency, filter, transform) and alpha clipping"
```

---

### Task 9: Semantic Layer Organization & Custom Hierarchies

**Files:**
- Create: `src/krita_mcp_lazy/layers/semantic.py`
- Modify: `src/krita_mcp_lazy/server/tools_layers.py`
- Test: `tests/unit/layers/test_semantic.py`

**Interfaces:**
- Consumes: `LayerService`, `MaskService`.
- Produces: `SemanticLayerOrganizer`, tools: `krita_scaffold_semantic_structure`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/layers/test_semantic.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.layers.semantic import SemanticLayerOrganizer

@pytest.mark.asyncio
async def test_scaffold_character_hierarchy():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"created_groups": 3, "created_layers": 8}
    
    organizer = SemanticLayerOrganizer(client=mock_client)
    schema = {
        "Character": {
            "Head": ["Hair", "Face", "Eyes", "Mouth"],
            "Body": ["Clothing", "Limbs", "Torso"]
        }
    }
    res = await organizer.scaffold_hierarchy(doc_id="doc_1", schema=schema)
    assert res["created_layers"] == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/layers/test_semantic.py -v`
Expected: FAIL

- [ ] **Step 3: Implement semantic hierarchy generator**

Build customizable hierarchy scaffolding without rigid hardcoded templates.
Support preset archetypes (`character_production`, `environment_depth`, `prop_asset`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/layers/test_semantic.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/layers/semantic.py tests/unit/layers/test_semantic.py
git commit -m "feat(layers): implement semantic layer scaffolding and custom hierarchy manager"
```

---

### Task 10: Brush Preset Discovery, Inspection & Parameter Configuration

**Files:**
- Create: `src/krita_mcp_lazy/painting/models.py`
- Create: `src/krita_mcp_lazy/painting/brush_service.py`
- Create: `src/krita_mcp_lazy/server/tools_painting.py`
- Test: `tests/unit/painting/test_brush_service.py`

**Interfaces:**
- Consumes: `AsyncIPCClient`.
- Produces: `BrushService`, `BrushPresetInfo`, tools: `krita_list_brush_presets`, `krita_select_brush_preset`, `krita_configure_brush`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/painting/test_brush_service.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.painting.brush_service import BrushService

@pytest.mark.asyncio
async def test_brush_preset_discovery():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "presets": [
            {"name": "b)_Basic-5_Size", "category": "Basic", "engine": "Pixel"},
            {"name": "c)_Pencil-2B", "category": "Pencil", "engine": "Pixel"}
        ]
    }
    
    svc = BrushService(client=mock_client)
    presets = await svc.list_presets(category="Basic")
    assert len(presets) == 2
    assert presets[0]["name"] == "b)_Basic-5_Size"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/painting/test_brush_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Brush Service**

Inspect installed Krita `KisPaintOpPreset`s.
Configure brush parameters: `size` (px), `opacity` (0.0-1.0), `flow` (0.0-1.0), `foreground_color` (RGB/Hex), `background_color`.
Register MCP tools in `tools_painting.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/painting/test_brush_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/painting/models.py src/krita_mcp_lazy/painting/brush_service.py src/krita_mcp_lazy/server/tools_painting.py tests/unit/painting
git commit -m "feat(painting): implement brush preset discovery and parameter configuration"
```

---

### Task 11: Native Stroke Generation, Pressure Simulation & Vector Path Automation

**Files:**
- Create: `src/krita_mcp_lazy/painting/stroke_engine.py`
- Modify: `src/krita_mcp_lazy/server/tools_painting.py`
- Test: `tests/unit/painting/test_stroke_engine.py`

**Interfaces:**
- Consumes: `BrushService`, `AsyncIPCClient`.
- Produces: `StrokeEngine`, `StrokePoint`, tools: `krita_paint_stroke`, `krita_paint_bezier_curve`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/painting/test_stroke_engine.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.painting.stroke_engine import StrokeEngine, StrokePoint

@pytest.mark.asyncio
async def test_native_stroke_execution():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"points_drawn": 4, "bounding_box": [10, 10, 100, 100]}
    
    engine = StrokeEngine(client=mock_client)
    points = [
        StrokePoint(x=10, y=10, pressure=0.2),
        StrokePoint(x=40, y=50, pressure=0.8),
        StrokePoint(x=80, y=90, pressure=0.6),
        StrokePoint(x=100, y=100, pressure=0.1)
    ]
    res = await engine.draw_stroke(doc_id="doc_1", layer_id="lyr_lineart", points=points)
    assert res["points_drawn"] == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/painting/test_stroke_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement native stroke engine**

Execute strokes using Krita's native stroke API or controlled input event synthesis dispatched on Krita's main thread.
Generate smoothed Bézier curves interpolated with pressure dynamics (tapered ends for inking/pencil).
Validate that strokes mutate layer pixels without substituting synthetic offscreen pixel blits.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/painting/test_stroke_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/painting/stroke_engine.py src/krita_mcp_lazy/server/tools_painting.py tests/unit/painting/test_stroke_engine.py
git commit -m "feat(painting): implement native stroke engine with pressure simulation and Bézier curves"
```

---

### Task 12: Visual Production Specification Generator (Art Direction & Planning)

**Files:**
- Create: `src/krita_mcp_lazy/art_planning/models.py`
- Create: `src/krita_mcp_lazy/art_planning/generator.py`
- Create: `src/krita_mcp_lazy/server/tools_art_planning.py`
- Test: `tests/unit/art_planning/test_art_planning.py`

**Interfaces:**
- Consumes: None (art planning engine).
- Produces: `ArtPlanner`, `VisualProductionSpec`, tools: `krita_generate_production_spec`, `krita_calculate_composition_grid`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/art_planning/test_art_planning.py
import pytest
from krita_mcp_lazy.art_planning.generator import ArtPlanner
from krita_mcp_lazy.art_planning.models import CompositionRule, StyleProfile

def test_generate_production_spec():
    planner = ArtPlanner()
    spec = planner.generate_spec(
        subject="Cyberpunk detective in rainy alley",
        aspect_ratio="16:9",
        canvas_width=3840,
        style=StyleProfile.ANIME_CINEMATIC,
        composition=CompositionRule.RULE_OF_THIRDS
    )
    assert spec.dimensions.width == 3840
    assert spec.dimensions.height == 2160
    assert len(spec.color_palette) >= 5
    assert spec.depth_plan.foreground is not None
    assert spec.depth_plan.background is not None
    assert len(spec.layer_blueprint) >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/art_planning/test_art_planning.py -v`
Expected: FAIL

- [ ] **Step 3: Implement art direction and composition engine**

Generate complete visual production specs:
- Aspect ratio calculations (16:9, 1:1, 4:3, 9:16).
- Rule of thirds focal coordinates, golden ratio spiral markers.
- Lighting scheme (key, fill, rim, bounce directions and color temperatures).
- Color harmony palettes (complementary, split-complementary, triadic, analogous).
- Layer blueprints mapped to depth planes.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/art_planning/test_art_planning.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/art_planning src/krita_mcp_lazy/server/tools_art_planning.py tests/unit/art_planning
git commit -m "feat(art_planning): implement visual production specification and composition grid generator"
```

---

### Task 13: Character Turnaround & Anatomical Construction Engine

**Files:**
- Create: `src/krita_mcp_lazy/character/models.py`
- Create: `src/krita_mcp_lazy/character/turnaround.py`
- Create: `src/krita_mcp_lazy/server/tools_character.py`
- Test: `tests/unit/character/test_turnaround.py`

**Interfaces:**
- Consumes: `DocumentService`, `LayerService`, `StrokeEngine`.
- Produces: `CharacterTurnaroundEngine`, tools: `krita_create_character_turnaround`, `krita_verify_character_consistency`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/character/test_turnaround.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.character.turnaround import CharacterTurnaroundEngine
from krita_mcp_lazy.character.models import CharacterSheetSpec, ViewAngle

@pytest.mark.asyncio
async def test_turnaround_sheet_generation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"views_created": ["front", "three_quarter", "side", "back"]}
    
    engine = CharacterTurnaroundEngine(client=mock_client)
    spec = CharacterSheetSpec(
        character_name="Kael",
        head_height_ratio=7.5,
        views=[ViewAngle.FRONT, ViewAngle.THREE_QUARTER, ViewAngle.SIDE, ViewAngle.BACK]
    )
    res = await engine.setup_turnaround_canvases(doc_id="doc_1", spec=spec)
    assert len(res["views_created"]) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/character/test_turnaround.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Character Turnaround Engine**

Calculate head-height anatomical proportions (6.5 to 8.0 heads).
Align eye-line, nose-line, chin-line, shoulder-line, waist-line, and ankle-line guides across all 4 view angles.
Maintain visual reference tokens for clothing, hair lock landmarks, and skin tones.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/character/test_turnaround.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/character src/krita_mcp_lazy/server/tools_character.py tests/unit/character
git commit -m "feat(character): implement character turnaround sheets and anatomical proportion engine"
```

---

### Task 14: Facial System, Expressions & Visemes Engine

**Files:**
- Create: `src/krita_mcp_lazy/character/expressions.py`
- Modify: `src/krita_mcp_lazy/server/tools_character.py`
- Test: `tests/unit/character/test_expressions.py`

**Interfaces:**
- Consumes: `CharacterTurnaroundEngine`, `LayerService`.
- Produces: `FacialExpressionEngine`, tools: `krita_create_expression_sheet`, `krita_generate_viseme_set`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/character/test_expressions.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.character.expressions import FacialExpressionEngine, EmotionType

@pytest.mark.asyncio
async def test_expression_sheet_generation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"emotions": ["neutral", "happy", "angry", "sad", "shocked", "scared"]}
    
    engine = FacialExpressionEngine(client=mock_client)
    res = await engine.create_expression_matrix(doc_id="doc_1", emotions=[
        EmotionType.NEUTRAL, EmotionType.HAPPY, EmotionType.ANGRY,
        EmotionType.SAD, EmotionType.SHOCKED, EmotionType.SCARED
    ])
    assert len(res["emotions"]) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/character/test_expressions.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Facial Expressions and Visemes**

Generate 6 core emotional variations and standard animation visemes (`AI`, `E`, `O`, `U`, `MBP`, `FV`, `LNTD`).
Scaffold dedicated eye, brow, and mouth sub-layers with precise anchor coordinates.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/character/test_expressions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/character/expressions.py tests/unit/character/test_expressions.py
git commit -m "feat(character): implement facial expressions and viseme generation engine"
```

---

### Task 15: Perspective Grids & Multi-Plane Environment Engine

**Files:**
- Create: `src/krita_mcp_lazy/environment/models.py`
- Create: `src/krita_mcp_lazy/environment/perspective.py`
- Create: `src/krita_mcp_lazy/server/tools_environment.py`
- Test: `tests/unit/environment/test_perspective.py`

**Interfaces:**
- Consumes: `DocumentService`, `LayerService`.
- Produces: `PerspectiveGridEngine`, `PerspectiveType`, tools: `krita_create_perspective_grid`, `krita_setup_environment_depth_planes`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/environment/test_perspective.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.environment.perspective import PerspectiveGridEngine, PerspectiveType

@pytest.mark.asyncio
async def test_two_point_perspective_grid():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "vp_left": [-500, 1080],
        "vp_right": [4340, 1080],
        "horizon_y": 1080,
        "grid_layer_id": "lyr_grid_2pt"
    }
    
    engine = PerspectiveGridEngine(client=mock_client)
    res = await engine.create_grid(
        doc_id="doc_1",
        p_type=PerspectiveType.TWO_POINT,
        horizon_y=1080,
        vp1_x=-500,
        vp2_x=4340
    )
    assert res["horizon_y"] == 1080
    assert "grid_layer_id" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/environment/test_perspective.py -v`
Expected: FAIL

- [ ] **Step 3: Implement perspective grid and depth plane generator**

Implement 1-point, 2-point, and 3-point perspective grid lines on non-printable guide layers.
Create structured depth planes (Sky, Far-BG, Mid-BG, Play-Area, Near-FG) with atmospheric perspective hazing.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/environment/test_perspective.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/environment src/krita_mcp_lazy/server/tools_environment.py tests/unit/environment
git commit -m "feat(environment): implement perspective grid generation and depth plane architecture"
```

---

### Task 16: Modular Prop Generator & Material Shading Engine

**Files:**
- Create: `src/krita_mcp_lazy/assets/models.py`
- Create: `src/krita_mcp_lazy/assets/prop_engine.py`
- Create: `src/krita_mcp_lazy/server/tools_assets.py`
- Test: `tests/unit/assets/test_prop_engine.py`

**Interfaces:**
- Consumes: `LayerService`, `BrushService`.
- Produces: `PropEngine`, `MaterialType`, tools: `krita_create_prop_asset`, `krita_apply_material_shading`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/assets/test_prop_engine.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.assets.prop_engine import PropEngine, MaterialType

@pytest.mark.asyncio
async def test_material_shading_setup():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "material": "wood",
        "shading_layers": ["Wood_Base", "Wood_Grain", "Wood_Shadow", "Wood_Highlight"]
    }
    
    engine = PropEngine(client=mock_client)
    res = await engine.setup_material_layers(doc_id="doc_1", prop_group_id="grp_table", material=MaterialType.WOOD)
    assert len(res["shading_layers"]) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/assets/test_prop_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Prop Engine and Material Shading**

Material profiles: `WOOD`, `METAL`, `FABRIC`, `GLASS`, `STONE`, `SKIN`, `WATER`.
Automatic setup of clipping shadow/highlight masks and texture brush assignments per material.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/assets/test_prop_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/assets src/krita_mcp_lazy/server/tools_assets.py tests/unit/assets
git commit -m "feat(assets): implement prop asset scaffolding and material shading engine"
```

---

### Task 17: Canvas Preview Capture & Visual Region Extraction

**Files:**
- Create: `src/krita_mcp_lazy/visual_qa/capture.py`
- Create: `src/krita_mcp_lazy/server/tools_visual_qa.py`
- Test: `tests/unit/visual_qa/test_capture.py`

**Interfaces:**
- Consumes: `AsyncIPCClient`.
- Produces: `VisualCaptureService`, tools: `krita_capture_preview`, `krita_extract_region`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/visual_qa/test_capture.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.visual_qa.capture import VisualCaptureService

@pytest.mark.asyncio
async def test_canvas_preview_capture():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "width": 1920,
        "height": 1080,
        "format": "PNG"
    }
    
    svc = VisualCaptureService(client=mock_client)
    preview = await svc.capture_canvas(doc_id="doc_1", max_dimension=1920)
    assert preview["format"] == "PNG"
    assert preview["width"] == 1920
    assert len(preview["image_base64"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/visual_qa/test_capture.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Visual Capture Service**

Export composite or designated layer bounds directly to memory as compressed PNG bytes.
Extract sub-regions (e.g. character face, hands, background props) for targeted QA inspection.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/visual_qa/test_capture.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/visual_qa/capture.py src/krita_mcp_lazy/server/tools_visual_qa.py tests/unit/visual_qa/test_capture.py
git commit -m "feat(visual_qa): implement canvas preview capture and regional visual extraction"
```

---

### Task 18: Quality Control Scorecard Evaluator & Surgical Rollback Engine

**Files:**
- Create: `src/krita_mcp_lazy/visual_qa/scorecard.py`
- Create: `src/krita_mcp_lazy/visual_qa/rollback.py`
- Modify: `src/krita_mcp_lazy/server/tools_visual_qa.py`
- Test: `tests/unit/visual_qa/test_scorecard.py`

**Interfaces:**
- Consumes: `VisualCaptureService`, `DocumentService`.
- Produces: `ScorecardEvaluator`, `CheckpointManager`, tools: `krita_evaluate_visual_quality`, `krita_create_checkpoint`, `krita_rollback_checkpoint`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/visual_qa/test_scorecard.py
import pytest
from krita_mcp_lazy.visual_qa.scorecard import ScorecardEvaluator, QualityCriteria

def test_scorecard_calculation():
    evaluator = ScorecardEvaluator()
    criteria = QualityCriteria(
        anatomy_proportions=90.0,
        line_quality=85.0,
        composition_perspective=88.0,
        lighting_shading=82.0,
        color_materials=85.0,
        reference_fidelity=90.0,
        detail_finish=80.0,
        layer_editability=95.0
    )
    score = evaluator.calculate_total(criteria)
    # Weights: 15, 15, 15, 15, 10, 15, 10, 5
    assert score >= 85.0
    assert evaluator.passes_production_gate(score) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/visual_qa/test_scorecard.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Scorecard Evaluator and Checkpoint Rollback**

Enforce the 8 weighted categories to hit >= 85/100 threshold.
Implement in-memory / fast `.kra` delta checkpoints before destructive paint operations; rollback on QA rejection.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/visual_qa/test_scorecard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/visual_qa/scorecard.py src/krita_mcp_lazy/visual_qa/rollback.py src/krita_mcp_lazy/server/tools_visual_qa.py tests/unit/visual_qa/test_scorecard.py
git commit -m "feat(visual_qa): implement 8-pillar quality scorecard and checkpoint rollback manager"
```

---

### Task 19: Raster Keyframe & Timing Engine with Memory Cache Guard

**Files:**
- Create: `src/krita_mcp_lazy/animation/models.py`
- Create: `src/krita_mcp_lazy/animation/keyframe_service.py`
- Create: `src/krita_mcp_lazy/server/tools_animation.py`
- Test: `tests/unit/animation/test_keyframe_service.py`

**Interfaces:**
- Consumes: `DocumentService`, `LayerService`.
- Produces: `KeyframeService`, tools: `krita_create_keyframe`, `krita_configure_onion_skin`, `krita_set_frame_timing`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/animation/test_keyframe_service.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.animation.keyframe_service import KeyframeService

@pytest.mark.asyncio
async def test_keyframe_creation_with_memory_guard():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {"frame_index": 24, "cache_usage_mb": 45.2, "status": "ok"}
    
    svc = KeyframeService(client=mock_client, max_cache_mb=500.0)
    res = await svc.create_keyframe(doc_id="doc_1", layer_id="lyr_anim", frame_index=24)
    assert res["frame_index"] == 24
    assert res["cache_usage_mb"] < 500.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/animation/test_keyframe_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement keyframe operations with RAM guard**

Manage raster animation frames: blank keyframe, duplicate keyframe, frame duration/hold.
Configure onion skinning (previous frames red, future frames green, opacity tint).
Enforce memory ceiling (~200 MiB/s budget guard) to prevent memory crashes on lengthy frame sets.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/animation/test_keyframe_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/animation/models.py src/krita_mcp_lazy/animation/keyframe_service.py src/krita_mcp_lazy/server/tools_animation.py tests/unit/animation
git commit -m "feat(animation): implement raster keyframe management with onion skin and RAM cache guard"
```

---

### Task 20: Frame Sequence Export & Validation Engine

**Files:**
- Create: `src/krita_mcp_lazy/animation/exporter.py`
- Modify: `src/krita_mcp_lazy/server/tools_animation.py`
- Test: `tests/unit/animation/test_exporter.py`

**Interfaces:**
- Consumes: `KeyframeService`, `AsyncIPCClient`.
- Produces: `SequenceExporter`, tools: `krita_export_frame_sequence`, `krita_validate_frame_sequence`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/animation/test_exporter.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.animation.exporter import SequenceExporter

@pytest.mark.asyncio
async def test_png_sequence_export():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "output_directory": "/tmp/anim_export",
        "frame_count": 24,
        "missing_frames": [],
        "zero_byte_frames": []
    }
    
    exporter = SequenceExporter(client=mock_client)
    res = await exporter.export_sequence(doc_id="doc_1", start_frame=0, end_frame=23, output_dir="/tmp/anim_export")
    assert res["frame_count"] == 24
    assert len(res["missing_frames"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/animation/test_exporter.py -v`
Expected: FAIL

- [ ] **Step 3: Implement PNG sequence export and validation**

Export numbered PNG sequences (`frame_0000.png` ... `frame_0023.png`).
Perform post-export validation: verify frame count, zero-byte file detection, and alpha integrity.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/animation/test_exporter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/animation/exporter.py tests/unit/animation/test_exporter.py
git commit -m "feat(animation): implement PNG sequence export and automated integrity validator"
```

---

### Task 21: Multi-Layer Asset Packaging & Pivot Metadata Exporter

**Files:**
- Create: `src/krita_mcp_lazy/interop_tahoma2d/models.py`
- Create: `src/krita_mcp_lazy/interop_tahoma2d/packager.py`
- Create: `src/krita_mcp_lazy/server/tools_tahoma2d.py`
- Test: `tests/unit/interop_tahoma2d/test_packager.py`

**Interfaces:**
- Consumes: `LayerService`, `DocumentService`.
- Produces: `AssetPackager`, `CutoutAssetMeta`, tools: `krita_package_tahoma2d_assets`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/interop_tahoma2d/test_packager.py
import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.interop_tahoma2d.packager import AssetPackager

@pytest.mark.asyncio
async def test_cutout_asset_packaging():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "manifest": {
            "character": "Hero",
            "parts": [
                {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
                {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4}
            ]
        }
    }
    
    packager = AssetPackager(client=mock_client)
    manifest = await packager.package_character_cutout(doc_id="doc_1", character_group="grp_hero", output_dir="/tmp/tahoma_pkg")
    assert manifest["character"] == "Hero"
    assert len(manifest["parts"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/interop_tahoma2d/test_packager.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Asset Packager for Tahoma2D**

Slice and export separate transparent PNG assets per body part/prop.
Generate metadata manifest JSON including normalized pivot points, z-order, and canvas offsets.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/interop_tahoma2d/test_packager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/interop_tahoma2d src/krita_mcp_lazy/server/tools_tahoma2d.py tests/unit/interop_tahoma2d
git commit -m "feat(tahoma2d): implement cutout asset packaging and pivot metadata exporter"
```

---

### Task 22: Tahoma2D Scene Project Generator & Round-Trip Validator

**Files:**
- Create: `src/krita_mcp_lazy/interop_tahoma2d/scene_builder.py`
- Modify: `src/krita_mcp_lazy/server/tools_tahoma2d.py`
- Test: `tests/unit/interop_tahoma2d/test_scene_builder.py`

**Interfaces:**
- Consumes: `AssetPackager`.
- Produces: `Tahoma2DSceneBuilder`, tools: `krita_build_tahoma2d_scene`, `krita_verify_tahoma2d_roundtrip`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/interop_tahoma2d/test_scene_builder.py
import pytest
from krita_mcp_lazy.interop_tahoma2d.scene_builder import Tahoma2DSceneBuilder

def test_scene_tnz_generation(tmp_path):
    builder = Tahoma2DSceneBuilder()
    manifest = {
        "character": "Hero",
        "parts": [
            {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
            {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4}
        ]
    }
    tnz_path = builder.generate_scene_xml(manifest=manifest, output_dir=str(tmp_path))
    assert tnz_path.endswith(".tnz")
    assert tmp_path.joinpath("scene.tnz").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/interop_tahoma2d/test_scene_builder.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Tahoma2D Scene generator and round-trip verification**

Generate standard Tahoma2D `.tnz` scene XML mapping columns, level paths, pegbar hierarchy, and stage positions.
Validate round-trip consistency (layer order, proportions, coordinate alignment).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/interop_tahoma2d/test_scene_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/interop_tahoma2d/scene_builder.py tests/unit/interop_tahoma2d/test_scene_builder.py
git commit -m "feat(tahoma2d): implement Tahoma2D scene XML builder and round-trip verification"
```

---

### Task 23: Monotonic Wall-Clock Telemetry, Memory & Operation Tracer

**Files:**
- Create: `src/krita_mcp_lazy/telemetry/tracker.py`
- Create: `src/krita_mcp_lazy/server/tools_telemetry.py`
- Test: `tests/unit/telemetry/test_tracker.py`

**Interfaces:**
- Consumes: None.
- Produces: `OperationTracker`, `StageMetric`, tools: `krita_get_telemetry_report`, `krita_reset_telemetry`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/telemetry/test_tracker.py
import pytest
import time
from krita_mcp_lazy.telemetry.tracker import OperationTracker

def test_wall_clock_tracking():
    tracker = OperationTracker()
    with tracker.track_stage("painting_stroke"):
        time.sleep(0.05)
        
    metrics = tracker.get_stage_metrics("painting_stroke")
    assert len(metrics) == 1
    assert metrics[0].duration_ms >= 45.0  # Real wall clock, not fake or estimated
    assert metrics[0].ram_usage_mb > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/telemetry/test_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Operation Tracker**

Use `time.perf_counter()` for monotonic high-resolution elapsed time.
Track system RAM via `psutil` or `resource`.
Record stage-level traces (Planning, Painting, Layer operations, Visual QA, Export).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/telemetry/test_tracker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/telemetry src/krita_mcp_lazy/server/tools_telemetry.py tests/unit/telemetry
git commit -m "feat(telemetry): implement real wall-clock stage telemetry and memory tracer"
```

---

### Task 24: 60 Dogfooding Challenges Runner & Production Benchmark Suite

**Files:**
- Create: `src/krita_mcp_lazy/dogfooding/runner.py`
- Create: `src/krita_mcp_lazy/dogfooding/challenges.py`
- Create: `tests/dogfooding/test_all_60_challenges.py`
- Test: `tests/dogfooding/test_all_60_challenges.py`

**Interfaces:**
- Consumes: All services (`DocumentService`, `LayerService`, `BrushService`, `StrokeEngine`, `ScorecardEvaluator`, `AssetPackager`, `OperationTracker`).
- Produces: `DogfoodingRunner`, `BenchmarkReport`, CLI benchmark tool.

- [ ] **Step 1: Write the failing test**

```python
# tests/dogfooding/test_all_60_challenges.py
import pytest
from krita_mcp_lazy.dogfooding.challenges import get_all_challenges
from krita_mcp_lazy.dogfooding.runner import DogfoodingRunner

def test_challenges_registry():
    challenges = get_all_challenges()
    assert len(challenges) == 60  # Exactly 60 benchmarks across 8 categories
    
    categories = {c.category for c in challenges}
    assert len(categories) == 8
    assert "character_illustration" in categories
    assert "environment_background" in categories
    assert "props_materials" in categories
    assert "drawing_intelligence" in categories
    assert "advanced_visual" in categories
    assert "document_stress" in categories
    assert "animation_production" in categories
    assert "visual_correction" in categories
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/dogfooding/test_all_60_challenges.py -v`
Expected: FAIL

- [ ] **Step 3: Implement 60 challenges and benchmark runner**

Implement registry of all 60 tests (01 to 60).
Implement runner executing each test against mock or live Krita IPC.
Aggregate technical and artistic scores into a final production report.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/dogfooding/test_all_60_challenges.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/krita_mcp_lazy/dogfooding tests/dogfooding
git commit -m "feat(dogfooding): implement 60-challenge benchmark suite and production test runner"
```

---

## Self-Review Checklist

1. **Spec Coverage:**
   - Foundation & IPC (Tasks 1-4) -> Phase 1.
   - Document & Canvas (Tasks 5-6) -> Phase 2.
   - Layers & Masks (Tasks 7-9) -> Phase 3.
   - Native Painting Engine (Tasks 10-11) -> Phase 4.
   - Art Direction & Composition (Task 12) -> Phase 5.
   - Professional Character (Tasks 13-14) -> Phase 6.
   - Environment & Props (Tasks 15-16) -> Phase 7.
   - Visual Intelligence & Scorecard (Tasks 17-18) -> Phase 8.
   - Animation & Sequence Export (Tasks 19-20) -> Phase 9.
   - Tahoma2D Interoperability (Tasks 21-22) -> Phase 10.
   - Telemetry & Performance (Task 23) -> Phase 11.
   - 60 Dogfooding Suite (Task 24) -> Phase 12.
2. **Step Scan:** Every step has an unambiguous failing test, command, expected fail/pass, and clear implementation/commit commands.
3. **Type Consistency:** Standardized on `JobRequest`, `JobResponse`, `KritaConfig`, `DocumentSpec`, `LayerSpec`, `StrokePoint`, and `QualityCriteria`.
4. **Review Focus:** Covered invalid tokens, Qt event loop deadlocks, memory cache caps on animation, rollback checkpoints, and KRA document round-trip fidelity.
5. **Proportion:** Rigorous, modular, and focused on interfaces, tests, and actions.
