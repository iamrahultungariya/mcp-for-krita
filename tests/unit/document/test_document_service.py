import pytest
from unittest.mock import AsyncMock
from pydantic import ValidationError
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.document.models import BitDepth, ColorModel, DocumentInfo, DocumentSpec
from krita_mcp_lazy.document.service import DocumentService
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_document_create_lifecycle():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="test_job_1",
        status=JobStatus.SUCCESS,
        result={
            "doc_id": "doc_hero_01",
            "name": "HeroShot",
            "width": 3840,
            "height": 2160,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB-elle-V2-srgbtrc.icc",
            "modified": False,
        },
    )

    svc = DocumentService(client=mock_client)
    spec = DocumentSpec(
        name="HeroShot",
        width=3840,
        height=2160,
        resolution_dpi=300,
        color_model=ColorModel.RGBA,
        bit_depth=BitDepth.U8,
    )
    doc_info = await svc.create_document(spec)

    assert doc_info["doc_id"] == "doc_hero_01"
    assert doc_info["width"] == 3840
    assert doc_info["height"] == 2160
    assert doc_info["color_model"] == "RGBA"
    mock_client.send_job.assert_called_once()
    
    # Verify sent action and params
    sent_req = mock_client.send_job.call_args[0][0]
    assert isinstance(sent_req, JobRequest)
    assert sent_req.action == "document.create"
    assert sent_req.params["width"] == 3840


@pytest.mark.asyncio
async def test_document_open_and_save():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="open_job",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_open_1", "file_path": "C:/art/scene.kra"},
        ),
        JobResponse(
            job_id="save_job",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_open_1", "file_path": "C:/art/scene.kra", "saved": True},
        ),
    ]

    svc = DocumentService(client=mock_client)
    open_res = await svc.open_document("C:/art/scene.kra")
    assert open_res["doc_id"] == "doc_open_1"

    save_res = await svc.save_document("doc_open_1", file_path="C:/art/scene.kra")
    assert save_res["saved"] is True
    assert mock_client.send_job.call_count == 2


@pytest.mark.asyncio
async def test_document_inspect_and_list():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="list_job",
            status=JobStatus.SUCCESS,
            result={"documents": [{"doc_id": "doc_1", "name": "Doc1"}]},
        ),
        JobResponse(
            job_id="inspect_job",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_1", "name": "Doc1", "width": 1920, "height": 1080},
        ),
    ]

    svc = DocumentService(client=mock_client)
    docs = await svc.list_documents()
    assert len(docs) == 1
    assert docs[0]["doc_id"] == "doc_1"

    doc = await svc.inspect_document("doc_1")
    assert doc["doc_id"] == "doc_1"
    assert doc["width"] == 1920


@pytest.mark.asyncio
async def test_document_service_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="fail_job",
        status=JobStatus.FAILED,
        error="Failed to create document: out of memory",
        error_code=ErrorCode.DOCUMENT_ERROR.value,
    )

    svc = DocumentService(client=mock_client)
    spec = DocumentSpec(width=1920, height=1080)
    with pytest.raises(KritaError) as exc_info:
        await svc.create_document(spec)
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR
    assert "out of memory" in exc_info.value.message


def test_document_spec_bounds_validation():
    # Valid spec
    spec = DocumentSpec(width=1920, height=1080, resolution_dpi=300.0)
    assert spec.width == 1920

    # Negative width
    with pytest.raises(ValidationError):
        DocumentSpec(width=-100, height=1080)

    # Exceeds max bounds (16384)
    with pytest.raises(ValidationError):
        DocumentSpec(width=20000, height=1080)


def test_document_registry_routing():
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    from plugins.krita_mcp_bridge.handlers_document import register_document_handlers, get_document_by_id, _mock_documents

    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    register_document_handlers(dispatcher)

    # Create two documents in mock mode
    req1 = JobRequest(action="document.create", params={"name": "Doc1", "width": 800, "height": 600})
    req2 = JobRequest(action="document.create", params={"name": "Doc2", "width": 1200, "height": 900})
    dispatcher.enqueue(req1)
    dispatcher.enqueue(req2)
    dispatcher.process_pending_jobs()

    res1 = dispatcher.get_result(req1.job_id).result
    res2 = dispatcher.get_result(req2.job_id).result

    doc1_id = res1["doc_id"]
    doc2_id = res2["doc_id"]

    assert doc1_id != doc2_id
    assert _mock_documents[doc1_id]["width"] == 800
    assert _mock_documents[doc2_id]["width"] == 1200

    # Inspect doc 1 specifically
    req_inspect = JobRequest(action="document.inspect", params={"doc_id": doc1_id})
    dispatcher.enqueue(req_inspect)
    dispatcher.process_pending_jobs()
    inspect_res = dispatcher.get_result(req_inspect.job_id).result
    assert inspect_res["name"] == "Doc1"
    assert inspect_res["width"] == 800

    # Close doc 1, doc 2 should remain
    req_close = JobRequest(action="document.close", params={"doc_id": doc1_id})
    dispatcher.enqueue(req_close)
    dispatcher.process_pending_jobs()
    assert doc1_id not in _mock_documents
    assert doc2_id in _mock_documents


@pytest.mark.asyncio
async def test_mcp_document_tools_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]
    
    assert "krita_create_document" in tool_names
    assert "krita_open_document" in tool_names
    assert "krita_save_document" in tool_names
    assert "krita_close_document" in tool_names
    assert "krita_inspect_document" in tool_names
    assert "krita_list_documents" in tool_names
