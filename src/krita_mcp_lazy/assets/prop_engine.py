"""Modular prop asset generation, material shading profiles, and layer templates."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.assets.models import MaterialType, PropSpec
from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient

MATERIAL_LAYER_TEMPLATES: Dict[MaterialType, List[str]] = {
    MaterialType.WOOD: ["Wood_Base", "Wood_Grain", "Wood_Shadow", "Wood_Highlight"],
    MaterialType.METAL: ["Metal_Base", "Metal_Reflection", "Metal_Shadow", "Metal_Specular_Highlight"],
    MaterialType.FABRIC: ["Fabric_Base", "Fabric_Texture_Weave", "Fabric_Shadow", "Fabric_Rim_Highlight"],
    MaterialType.GLASS: ["Glass_Base", "Glass_Transparency", "Glass_Refraction", "Glass_Specular"],
    MaterialType.STONE: ["Stone_Base", "Stone_Cracks_Texture", "Stone_Occlusion", "Stone_Highlight"],
    MaterialType.SKIN: ["Skin_Base", "Subsurface_Scatter", "Skin_Core_Shadow", "Skin_Specular"],
    MaterialType.WATER: ["Water_Depth_Base", "Water_Caustics", "Water_Reflection", "Water_Foam_Highlight"],
}


class PropEngine:
    """Manages modular prop assets, material shading layers, and texture assignments."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def create_prop_asset(
        self,
        doc_id: str,
        prop_name: str,
        material: MaterialType = MaterialType.WOOD,
        category: str = "General",
        bounding_box: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Scaffold a self-contained prop asset hierarchy with material shading layers."""
        shading_layers = MATERIAL_LAYER_TEMPLATES.get(material, ["Base", "Shadow", "Highlight"])
        layers_created = [f"{prop_name}_Lines"] + shading_layers

        payload = {
            "doc_id": doc_id,
            "prop_name": prop_name,
            "material": material.value,
            "category": category,
            "bounding_box": bounding_box,
            "shading_layers": shading_layers,
            "layers_created": layers_created,
        }

        resp = await self.client.send_job("assets.create_prop", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Prop creation failed")

    async def setup_material_layers(
        self,
        doc_id: str,
        prop_group_id: str,
        material: MaterialType = MaterialType.WOOD,
    ) -> Dict[str, Any]:
        """Apply material-specific shading layers (base, shadow, occlusion, highlight) to an existing prop group."""
        shading_layers = MATERIAL_LAYER_TEMPLATES.get(material, ["Base", "Shadow", "Highlight"])

        payload = {
            "doc_id": doc_id,
            "prop_group_id": prop_group_id,
            "material": material.value,
            "shading_layers": shading_layers,
        }

        resp = await self.client.send_job("assets.setup_material", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Material setup failed")
