import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.layers.masks import MaskService, MaskType
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_transparency_and_filter_masks():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_mask_1",
            status=JobStatus.SUCCESS,
            result={"mask_id": "mask_trans_01", "parent_layer_id": "lyr_hair", "mask_type": "transparency"},
        ),
        JobResponse(
            job_id="job_mask_2",
            status=JobStatus.SUCCESS,
            result={"mask_id": "mask_filter_01", "parent_layer_id": "lyr_bg", "mask_type": "filter"},
        ),
    ]

    svc = MaskService(client=mock_client)
    res1 = await svc.add_mask(
        doc_id="doc_1",
        layer_id="lyr_hair",
        mask_type=MaskType.TRANSPARENCY,
        name="Hair_Shading_Mask",
    )
    assert res1["mask_id"] == "mask_trans_01"
    assert res1["mask_type"] == "transparency"

    res2 = await svc.add_mask(
        doc_id="doc_1",
        layer_id="lyr_bg",
        mask_type=MaskType.FILTER,
        name="Blur_Mask",
        filter_config={"filter_name": "blur", "radius": 5.0},
    )
    assert res2["mask_id"] == "mask_filter_01"


@pytest.mark.asyncio
async def test_alpha_inheritance():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_alpha",
        status=JobStatus.SUCCESS,
        result={"layer_id": "lyr_shadow", "inherit_alpha": True, "updated": True},
    )

    svc = MaskService(client=mock_client)
    res = await svc.set_alpha_inheritance(doc_id="doc_1", layer_id="lyr_shadow", inherit_alpha=True)
    assert res["inherit_alpha"] is True
    assert res["updated"] is True

    sent_req = mock_client.send_job.call_args[0][0]
    assert sent_req.action == "layer.alpha_inheritance"
    assert sent_req.params["inherit_alpha"] is True


@pytest.mark.asyncio
async def test_remove_and_list_masks():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_list_masks",
            status=JobStatus.SUCCESS,
            result={"masks": [{"mask_id": "m1", "name": "Mask 1", "type": "transparency"}]},
        ),
        JobResponse(
            job_id="job_remove_mask",
            status=JobStatus.SUCCESS,
            result={"mask_id": "m1", "removed": True},
        ),
    ]

    svc = MaskService(client=mock_client)
    masks = await svc.list_masks(doc_id="doc_1", layer_id="lyr_1")
    assert len(masks) == 1
    assert masks[0]["mask_id"] == "m1"

    rem_res = await svc.remove_mask(doc_id="doc_1", mask_id="m1")
    assert rem_res["removed"] is True


@pytest.mark.asyncio
async def test_mask_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_err",
        status=JobStatus.FAILED,
        error="Target layer for mask does not exist",
        error_code=ErrorCode.LAYER_ERROR.value,
    )

    svc = MaskService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await svc.add_mask(doc_id="doc_1", layer_id="missing_layer", mask_type=MaskType.TRANSPARENCY)
    assert exc_info.value.code == ErrorCode.LAYER_ERROR
    assert "Target layer" in exc_info.value.message


@pytest.mark.asyncio
async def test_mcp_mask_tools_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]

    assert "krita_add_mask" in tool_names
    assert "krita_remove_mask" in tool_names
    assert "krita_set_alpha_inheritance" in tool_names
    assert "krita_list_masks" in tool_names
