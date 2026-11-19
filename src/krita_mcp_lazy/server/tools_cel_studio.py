"""FastMCP tools for autonomous studio cel drawing, modular animation rigs, and fidelity verification."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from krita_mcp_lazy.cel_engine.decomposer import CelArtDecomposer
from krita_mcp_lazy.cel_engine.fidelity import FidelityGate
from krita_mcp_lazy.cel_engine.models import CelArtDecomposition
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.modular_rig.models import CharacterRigMetadata
from krita_mcp_lazy.modular_rig.packager import ModularRigPackager
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


def _render_composite_layers(
    decomp: CelArtDecomposition,
    output_path: str,
) -> str:
    """Render full composite of all decomposed layers into high-resolution PNG."""
    w, h = decomp.width, decomp.height

    # Start with white base canvas
    composite = np.full((h, w, 3), 255, dtype=np.uint8)

    # 1. Trapped Flats
    if decomp.composite_flats is not None:
        flats_rgb = decomp.composite_flats[:, :, :3]
        composite = flats_rgb.copy()

    # 2. Cel Shadows (Multiply blend)
    if decomp.composite_shadows is not None:
        shadow_mask = decomp.composite_shadows[:, :, 3] > 0
        shadow_rgb = decomp.composite_shadows[:, :, :3].astype(np.float32)
        comp_float = composite.astype(np.float32)

        # Multiply blending formula: (base * shadow) / 255
        multiplied = (comp_float * shadow_rgb) / 255.0
        alpha = (decomp.composite_shadows[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]

        blended = comp_float * (1.0 - alpha) + multiplied * alpha
        composite[shadow_mask] = np.clip(blended[shadow_mask], 0, 255).astype(np.uint8)

    # 3. Master Lineart (Rich ink)
    if decomp.composite_lineart is not None:
        line_mask = decomp.composite_lineart[:, :, 3] > 0
        composite[line_mask] = decomp.composite_lineart[line_mask, :3]
    elif decomp.lineart_mask is not None:
        line_mask = decomp.lineart_mask > 0
        composite[line_mask] = [20, 18, 24]

    # 4. Highlights / Rim Light (Screen/Addition blend)
    if decomp.composite_highlights is not None:
        hl_mask = decomp.composite_highlights[:, :, 3] > 0
        hl_rgb = decomp.composite_highlights[:, :, :3].astype(np.float32)
        comp_float = composite.astype(np.float32)

        # Screen blend: 255 - ((255 - base) * (255 - blend) / 255)
        screened = 255.0 - ((255.0 - comp_float) * (255.0 - hl_rgb) / 255.0)
        alpha = (decomp.composite_highlights[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]

        blended = comp_float * (1.0 - alpha) + screened * alpha
        composite[hl_mask] = np.clip(blended[hl_mask], 0, 255).astype(np.uint8)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, composite)
    logger.info("Saved studio cel composite to %s", output_path)
    return output_path


async def live_paint_anime_character(
    image_path: str,
    doc_id: str = "doc_cel_01",
    client: Optional[Any] = None,
    use_live_tablet: bool = False,
    char_id: str = "anime_creator",
    char_name: str = "Anime Creator",
    output_png_path: Optional[str] = None,
    library_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute autonomous Studio Cel-Hybrid anime drawing & painting pipeline."""
    logger.info("Starting live paint anime pipeline for %s...", image_path)

    # 1. Computer Vision Cel Decomposition
    decomposer = CelArtDecomposer(trapping_dilation_px=2)
    decomp = decomposer.decompose(image_path)

    # 2. Connect IPC client if not provided
    ipc_client = client
    own_client = False
    if ipc_client is None:
        ipc_client = AsyncIPCClient()
        await ipc_client.connect()
        own_client = True

    try:
        # 3. Create or verify document in Krita
        await ipc_client.send_job(
            "document.create",
            {
                "doc_id": doc_id,
                "width": decomp.width,
                "height": decomp.height,
                "resolution": 300,
                "name": f"Studio_Cel_{doc_id}",
            },
        )

        # 4. Extract dominant palette & scaffold Modular Character Rig
        palette: Dict[str, str] = {}
        for idx, fl in enumerate(decomp.flat_regions[:10]):
            palette[f"color_{idx:02d}"] = fl.color_hex

        bounds = {
            "x": 0.0,
            "y": 0.0,
            "width": float(decomp.width),
            "height": float(decomp.height),
        }

        meta = CharacterRigMetadata(
            character_id=char_id,
            name=char_name,
            style="rg_bucket_list",
            palette=palette,
            bounds=bounds,
            pivots={
                "neck": [round(decomp.width * 0.5, 1), round(decomp.height * 0.48, 1)],
                "shoulder_l": [round(decomp.width * 0.32, 1), round(decomp.height * 0.52, 1)],
                "shoulder_r": [round(decomp.width * 0.68, 1), round(decomp.height * 0.52, 1)],
            },
        )

        packager = ModularRigPackager(
            ipc_client,
            library_root=library_root or "asset_library/characters",
        )
        rig_scaffold = await packager.scaffold_rig_tree(doc_id, meta)

        # 5. Push Trapped Flats Layer (BGRA byte sanitization)
        if decomp.composite_flats is not None:
            # Convert RGBA to Krita BGRA byte ordering
            flats_bgra = cv2.cvtColor(decomp.composite_flats, cv2.COLOR_RGBA2BGRA)
            _, buf = cv2.imencode(".png", flats_bgra)
            b64_data = base64.b64encode(buf).decode("ascii")

            await ipc_client.send_job(
                "layer.create",
                {
                    "doc_id": doc_id,
                    "name": "02_Flat_Colors",
                    "layer_type": "paintLayer",
                    "parent_group": "Char_Main_Rig",
                },
            )
            await ipc_client.send_job(
                "layer.set_pixel_tile",
                {
                    "doc_id": doc_id,
                    "layer_name": "02_Flat_Colors",
                    "tile_index": 0,
                    "x": 0,
                    "y": 0,
                    "width": decomp.width,
                    "height": decomp.height,
                    "data_base64": b64_data,
                },
            )

        # 6. Push Cel-Shadows Layer (Multiply with inheritAlpha=True)
        if decomp.composite_shadows is not None:
            shadows_bgra = cv2.cvtColor(decomp.composite_shadows, cv2.COLOR_RGBA2BGRA)
            _, buf = cv2.imencode(".png", shadows_bgra)
            b64_data = base64.b64encode(buf).decode("ascii")

            await ipc_client.send_job(
                "layer.create",
                {
                    "doc_id": doc_id,
                    "name": "03_Cel_Shadows",
                    "layer_type": "paintLayer",
                    "parent_group": "Char_Main_Rig",
                    "blending_mode": "multiply",
                },
            )
            await ipc_client.send_job(
                "layer.set_inherit_alpha",
                {
                    "doc_id": doc_id,
                    "layer_name": "03_Cel_Shadows",
                    "inherit_alpha": True,
                },
            )
            await ipc_client.send_job(
                "layer.set_pixel_tile",
                {
                    "doc_id": doc_id,
                    "layer_name": "03_Cel_Shadows",
                    "tile_index": 0,
                    "x": 0,
                    "y": 0,
                    "width": decomp.width,
                    "height": decomp.height,
                    "data_base64": b64_data,
                },
            )

        # 7. Push Inking Lineart Layer (Synthetic QTabletEvent or SVG Vector)
        await ipc_client.send_job(
            "layer.create",
            {
                "doc_id": doc_id,
                "name": "04_Master_Lineart",
                "layer_type": "paintLayer",
                "parent_group": "Char_Main_Rig",
            },
        )

        if use_live_tablet and len(decomp.vector_strokes) > 0:
            logger.info("Executing %d live tablet strokes in Krita...", len(decomp.vector_strokes))
            for st in decomp.vector_strokes:
                await ipc_client.send_job(
                    "stroke.live_tablet_stroke",
                    {
                        "doc_id": doc_id,
                        "layer_name": "04_Master_Lineart",
                        "points": st.points,
                        "pressures": st.pressures,
                        "brush_preset": st.brush_preset,
                        "color": st.color,
                        "base_width": st.base_width,
                    },
                )
        else:
            # Fallback to high-speed raster / vector tile push
            line_rgba = np.zeros((decomp.height, decomp.width, 4), dtype=np.uint8)
            line_rgba[decomp.lineart_mask > 0] = [0, 0, 0, 255]
            line_bgra = cv2.cvtColor(line_rgba, cv2.COLOR_RGBA2BGRA)
            _, buf = cv2.imencode(".png", line_bgra)
            b64_data = base64.b64encode(buf).decode("ascii")

            await ipc_client.send_job(
                "layer.set_pixel_tile",
                {
                    "doc_id": doc_id,
                    "layer_name": "04_Master_Lineart",
                    "tile_index": 0,
                    "x": 0,
                    "y": 0,
                    "width": decomp.width,
                    "height": decomp.height,
                    "data_base64": b64_data,
                },
            )

        # 8. Push Highlights / Rim Light Layer (Screen/Addition blend)
        if decomp.composite_highlights is not None:
            hl_bgra = cv2.cvtColor(decomp.composite_highlights, cv2.COLOR_RGBA2BGRA)
            _, buf = cv2.imencode(".png", hl_bgra)
            b64_data = base64.b64encode(buf).decode("ascii")

            await ipc_client.send_job(
                "layer.create",
                {
                    "doc_id": doc_id,
                    "name": "05_Highlights_RimLight",
                    "layer_type": "paintLayer",
                    "parent_group": "Char_Main_Rig",
                    "blending_mode": "addition",
                },
            )
            await ipc_client.send_job(
                "layer.set_pixel_tile",
                {
                    "doc_id": doc_id,
                    "layer_name": "05_Highlights_RimLight",
                    "tile_index": 0,
                    "x": 0,
                    "y": 0,
                    "width": decomp.width,
                    "height": decomp.height,
                    "data_base64": b64_data,
                },
            )

        # 9. Render composite image & evaluate fidelity
        if not output_png_path:
            os.makedirs("output", exist_ok=True)
            output_png_path = os.path.join("output", f"painted_cel_{doc_id}.png")

        _render_composite_layers(decomp, output_png_path)

        gate = FidelityGate(min_ssim=0.88, min_edge_iou=0.80)
        report = gate.evaluate(image_path, output_png_path)

        # 10. Export reusable modular rig manifest
        manifest_path = packager.export_manifest(meta)

        return {
            "success": True,
            "doc_id": doc_id,
            "char_id": char_id,
            "vector_strokes_count": len(decomp.vector_strokes),
            "flats_count": len(decomp.flat_regions),
            "fidelity": report.to_dict(),
            "manifest_path": manifest_path,
            "output_png_path": output_png_path,
            "rig_groups": rig_scaffold.get("groups_created", 0),
        }
    finally:
        if own_client and ipc_client is not None:
            await ipc_client.disconnect()


async def export_reusable_rig(
    char_id: str,
    name: str = "Anime Character",
    doc_id: str = "doc_cel_01",
    client: Optional[Any] = None,
    library_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Export rig manifest and modular metadata for cross-scene reuse."""
    ipc_client = client
    own_client = False
    if ipc_client is None:
        ipc_client = AsyncIPCClient()
        await ipc_client.connect()
        own_client = True

    try:
        packager = ModularRigPackager(
            ipc_client,
            library_root=library_root or "asset_library/characters",
        )
        meta = CharacterRigMetadata(
            character_id=char_id,
            name=name,
        )
        manifest_path = packager.export_manifest(meta)
        return {
            "success": True,
            "character_id": char_id,
            "manifest_path": manifest_path,
        }
    finally:
        if own_client and ipc_client is not None:
            await ipc_client.disconnect()


async def import_reusable_rig(
    char_id: str,
    doc_id: str,
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    client: Optional[Any] = None,
    library_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Import and scaffold an existing modular rig into the active Krita document."""
    ipc_client = client
    own_client = False
    if ipc_client is None:
        ipc_client = AsyncIPCClient()
        await ipc_client.connect()
        own_client = True

    try:
        packager = ModularRigPackager(
            ipc_client,
            library_root=library_root or "asset_library/characters",
        )
        res = await packager.import_rig(doc_id, char_id, x, y, scale)
        return res
    finally:
        if own_client and ipc_client is not None:
            await ipc_client.disconnect()


def verify_canvas_fidelity(
    ref_path: str,
    render_path: str,
    min_ssim: float = 0.88,
    min_edge_iou: float = 0.80,
) -> Dict[str, Any]:
    """Evaluate fidelity between reference image and rendered canvas."""
    gate = FidelityGate(min_ssim=min_ssim, min_edge_iou=min_edge_iou)
    report = gate.evaluate(ref_path, render_path)
    return report.to_dict()


def register_cel_studio_tools(server: Any, config: KritaConfig) -> None:
    """Register all Studio Cel-Hybrid drawing and animation rig tools with FastMCP."""

    @server.tool()
    async def krita_live_paint_anime_character(
        image_path: str,
        doc_id: str = "doc_cel_01",
        use_live_tablet: bool = False,
        char_id: str = "anime_creator",
        char_name: str = "Anime Creator",
    ) -> Dict[str, Any]:
        """Autonomously paints an anime character layer-by-layer matching reference with real G-Pen brushes."""
        return await live_paint_anime_character(
            image_path=image_path,
            doc_id=doc_id,
            use_live_tablet=use_live_tablet,
            char_id=char_id,
            char_name=char_name,
        )

    @server.tool()
    async def krita_export_reusable_rig(
        char_id: str,
        name: str = "Anime Character",
        doc_id: str = "doc_cel_01",
    ) -> Dict[str, Any]:
        """Exports a character's modular layer hierarchy, pivots, and color palette into a reusable asset."""
        return await export_reusable_rig(
            char_id=char_id,
            name=name,
            doc_id=doc_id,
        )

    @server.tool()
    async def krita_import_reusable_rig(
        char_id: str,
        doc_id: str,
        x: int = 0,
        y: int = 0,
        scale: float = 1.0,
    ) -> Dict[str, Any]:
        """Imports an existing modular character rig into a target Krita document."""
        return await import_reusable_rig(
            char_id=char_id,
            doc_id=doc_id,
            x=x,
            y=y,
            scale=scale,
        )

    @server.tool()
    def krita_verify_fidelity(
        ref_path: str,
        render_path: str,
        min_ssim: float = 0.88,
        min_edge_iou: float = 0.80,
    ) -> Dict[str, Any]:
        """Certifies visual reproduction accuracy against reference using SSIM and Edge IoU."""
        return verify_canvas_fidelity(
            ref_path=ref_path,
            render_path=render_path,
            min_ssim=min_ssim,
            min_edge_iou=min_edge_iou,
        )
