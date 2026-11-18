import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.assets.models import MaterialType
from krita_mcp_lazy.assets.prop_engine import PropEngine
from krita_mcp_lazy.core.errors import ErrorCode, KritaError


@pytest.mark.asyncio
async def test_material_shading_setup():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "material": "wood",
        "prop_group_id": "grp_table",
        "shading_layers": ["Wood_Base", "Wood_Grain", "Wood_Shadow", "Wood_Highlight"],
    }

    engine = PropEngine(client=mock_client)
    res = await engine.setup_material_layers(
        doc_id="doc_1",
        prop_group_id="grp_table",
        material=MaterialType.WOOD,
    )
    assert res["material"] == "wood"
    assert len(res["shading_layers"]) == 4
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "assets.setup_material"


@pytest.mark.asyncio
async def test_create_prop_asset():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "prop_name": "Ancient_Sword",
        "prop_group_id": "Ancient_Sword_Asset",
        "material": "metal",
        "layers_created": ["Ancient_Sword_Lines", "Metal_Base", "Metal_Reflection", "Metal_Shadow", "Metal_Specular_Highlight"],
    }

    engine = PropEngine(client=mock_client)
    res = await engine.create_prop_asset(
        doc_id="doc_1",
        prop_name="Ancient_Sword",
        material=MaterialType.METAL,
        category="Weapon",
    )
    assert res["prop_name"] == "Ancient_Sword"
    assert res["material"] == "metal"
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "assets.create_prop"


@pytest.mark.asyncio
async def test_prop_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Group grp_invalid not found",
    }

    engine = PropEngine(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await engine.setup_material_layers(doc_id="doc_1", prop_group_id="grp_invalid")
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_assets_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_create_prop_asset" in tool_names
    assert "krita_apply_material_shading" in tool_names
