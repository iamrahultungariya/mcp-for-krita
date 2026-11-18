import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.layers.models import BlendingMode, LayerSpec, LayerType, ReorderPosition
from krita_mcp_lazy.layers.service import LayerService
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_layer_creation_and_tree_inspection():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_tree_1",
        status=JobStatus.SUCCESS,
        result={
            "layers": [
                {
                    "id": "grp_character",
                    "name": "Character",
                    "type": "group",
                    "children": [
                        {"id": "lyr_lineart", "name": "LineArt", "type": "paint", "opacity": 255, "blending_mode": "normal"},
                        {"id": "lyr_color", "name": "Color", "type": "paint", "opacity": 255, "blending_mode": "normal"},
                    ],
                }
            ]
        },
    )

    svc = LayerService(client=mock_client)
    tree = await svc.inspect_layer_tree(doc_id="doc_1")
    assert len(tree["layers"]) == 1
    assert tree["layers"][0]["name"] == "Character"
    assert len(tree["layers"][0]["children"]) == 2
    assert tree["layers"][0]["children"][0]["name"] == "LineArt"


@pytest.mark.asyncio
async def test_layer_create():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_create_lyr",
        status=JobStatus.SUCCESS,
        result={"layer_id": "lyr_shading", "name": "Shading", "type": "paint", "created": True},
    )

    svc = LayerService(client=mock_client)
    spec = LayerSpec(
        name="Shading",
        type=LayerType.PAINT,
        opacity=200,
        blending_mode=BlendingMode.MULTIPLY,
        parent_group="Character",
    )
    res = await svc.create_layer(doc_id="doc_1", spec=spec)
    assert res["created"] is True
    assert res["name"] == "Shading"

    sent_req = mock_client.send_job.call_args[0][0]
    assert sent_req.action == "layer.create"
    assert sent_req.params["blending_mode"] == "multiply"
    assert sent_req.params["opacity"] == 200


@pytest.mark.asyncio
async def test_layer_reorder_and_delete():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_reorder",
            status=JobStatus.SUCCESS,
            result={"target": "LineArt", "reference": "Color", "position": "above", "reordered": True},
        ),
        JobResponse(
            job_id="job_delete",
            status=JobStatus.SUCCESS,
            result={"layer_name": "Sketch", "deleted": True},
        ),
    ]

    svc = LayerService(client=mock_client)
    reorder_res = await svc.reorder_layer(
        doc_id="doc_1",
        target_layer="LineArt",
        reference_layer="Color",
        position=ReorderPosition.ABOVE,
    )
    assert reorder_res["reordered"] is True

    delete_res = await svc.delete_layer(doc_id="doc_1", layer_name="Sketch")
    assert delete_res["deleted"] is True


@pytest.mark.asyncio
async def test_layer_set_properties_and_active():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_props",
            status=JobStatus.SUCCESS,
            result={"layer_name": "LineArt", "opacity": 180, "visible": True, "updated": True},
        ),
        JobResponse(
            job_id="job_active",
            status=JobStatus.SUCCESS,
            result={"layer_name": "LineArt", "active": True},
        ),
    ]

    svc = LayerService(client=mock_client)
    prop_res = await svc.set_layer_properties(doc_id="doc_1", layer_name="LineArt", opacity=180, visible=True)
    assert prop_res["updated"] is True

    active_res = await svc.set_active_layer(doc_id="doc_1", layer_name="LineArt")
    assert active_res["active"] is True


@pytest.mark.asyncio
async def test_layer_service_error_handling():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_err",
        status=JobStatus.FAILED,
        error="Layer 'NonExistent' does not exist in document",
        error_code=ErrorCode.LAYER_ERROR.value,
    )

    svc = LayerService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await svc.delete_layer(doc_id="doc_1", layer_name="NonExistent")
    assert exc_info.value.code == ErrorCode.LAYER_ERROR
    assert "does not exist" in exc_info.value.message


@pytest.mark.asyncio
async def test_mcp_layer_tools_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]

    assert "krita_create_layer" in tool_names
    assert "krita_delete_layer" in tool_names
    assert "krita_reorder_layer" in tool_names
    assert "krita_inspect_layer_tree" in tool_names
    assert "krita_set_layer_properties" in tool_names
    assert "krita_set_active_layer" in tool_names
