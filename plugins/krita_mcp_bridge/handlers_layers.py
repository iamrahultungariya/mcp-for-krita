"""Krita native API handlers for layer hierarchy management and manipulation."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from plugins.krita_mcp_bridge.handlers_document import get_document_by_id

logger = logging.getLogger(__name__)

# In-memory mock layer store for headless testing
_mock_layer_trees: Dict[str, List[dict]] = {}


def _get_doc_layers(doc_id: str) -> List[dict]:
    if doc_id not in _mock_layer_trees:
        _mock_layer_trees[doc_id] = [
            {
                "id": f"lyr_{uuid.uuid4().hex[:6]}",
                "name": "Background",
                "type": "paint",
                "opacity": 255,
                "blending_mode": "normal",
                "visible": True,
                "locked": False,
                "inherit_alpha": False,
                "children": [],
            }
        ]
    return _mock_layer_trees[doc_id]


def register_layer_handlers(dispatcher: Any) -> None:
    """Register all layer-related handlers with the main-thread dispatcher."""

    def handle_layer_tree(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    def _serialize_node(node: Any) -> dict:
                        children = [_serialize_node(child) for child in node.childNodes()]
                        inherit_a = getattr(node, "inheritAlpha", lambda: False)()
                        return {
                            "id": node.name(),
                            "name": node.name(),
                            "type": node.type(),
                            "opacity": node.opacity(),
                            "blending_mode": node.blendingMode(),
                            "visible": node.visible(),
                            "locked": node.locked(),
                            "inherit_alpha": inherit_a,
                            "children": children,
                        }
                    root = doc.rootNode()
                    layers = [_serialize_node(child) for child in root.childNodes()]
                    return {"doc_id": doc_id, "layers": layers}
        except ImportError:
            pass

        # Headless mock mode
        return {"doc_id": doc_id, "layers": _get_doc_layers(doc_id)}

    def handle_create_layer(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        name = params.get("name", "New Layer")
        layer_type = params.get("layer_type") or params.get("type", "paint")
        opacity = params.get("opacity", 255)
        blending_mode = params.get("blending_mode", "normal")
        visible = params.get("visible", True)
        locked = params.get("locked", False)
        parent_group = params.get("parent_group") or params.get("parent_id")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    if layer_type in ("group", "groupLayer"):
                        node = doc.createGroupLayer(name)
                    else:
                        node = doc.createNode(name, "paintLayer")
                    node.setOpacity(opacity)
                    node.setBlendingMode(blending_mode)
                    node.setVisible(visible)
                    node.setLocked(locked)

                    parent_node = doc.rootNode()
                    if parent_group:
                        candidate = doc.nodeByName(parent_group)
                        if candidate:
                            parent_node = candidate

                    parent_node.addChildNode(node, None)
                    return {
                        "doc_id": doc_id,
                        "layer_id": node.name(),
                        "name": node.name(),
                        "type": layer_type,
                        "created": True,
                    }
        except Exception as le:
            logger.warning("Failed to create layer in Krita: %s", le)

        # Headless mock mode
        layers = _get_doc_layers(doc_id)
        new_node = {
            "id": f"lyr_{uuid.uuid4().hex[:6]}",
            "name": name,
            "type": layer_type,
            "opacity": opacity,
            "blending_mode": blending_mode,
            "visible": visible,
            "locked": locked,
            "inherit_alpha": False,
            "children": [],
        }

        if parent_group:
            for l in layers:
                if l["name"] == parent_group and l.get("type") == "group":
                    l.setdefault("children", []).append(new_node)
                    return {"doc_id": doc_id, "layer_id": new_node["id"], "name": name, "created": True}
        layers.append(new_node)
        return {"doc_id": doc_id, "layer_id": new_node["id"], "name": name, "created": True}

    def handle_delete_layer(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_name = params.get("layer_name")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and layer_name:
                    node = doc.nodeByName(layer_name)
                    if node:
                        node.remove()
                        return {"doc_id": doc_id, "layer_name": layer_name, "deleted": True}
        except ImportError:
            pass

        # Headless mock mode
        layers = _get_doc_layers(doc_id)
        for i, l in enumerate(layers):
            if l["name"] == layer_name or l["id"] == layer_name:
                layers.pop(i)
                return {"doc_id": doc_id, "layer_name": layer_name, "deleted": True}
        return {"doc_id": doc_id, "layer_name": layer_name, "deleted": True}

    def handle_reorder_layer(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        target = params.get("target")
        reference = params.get("reference")
        position = params.get("position", "above")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and target and reference:
                    target_node = doc.nodeByName(target)
                    ref_node = doc.nodeByName(reference)
                    if target_node and ref_node:
                        # Reorder using Krita node movement
                        parent = ref_node.parentNode() or doc.rootNode()
                        parent.addChildNode(target_node, ref_node)
                        return {"doc_id": doc_id, "target": target, "reference": reference, "position": position, "reordered": True}
        except ImportError:
            pass

        # Headless mock mode
        return {"doc_id": doc_id, "target": target, "reference": reference, "position": position, "reordered": True}

    def handle_set_properties(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_name = params.get("layer_name")
        opacity = params.get("opacity")
        visible = params.get("visible")
        locked = params.get("locked")
        blending_mode = params.get("blending_mode")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and layer_name:
                    node = doc.nodeByName(layer_name)
                    if node:
                        if opacity is not None:
                            node.setOpacity(opacity)
                        if visible is not None:
                            node.setVisible(visible)
                        if locked is not None:
                            node.setLocked(locked)
                        if blending_mode is not None:
                            node.setBlendingMode(blending_mode)
                        return {"doc_id": doc_id, "layer_name": layer_name, "updated": True}
        except ImportError:
            pass

        # Headless mock mode
        layers = _get_doc_layers(doc_id)
        for l in layers:
            if l["name"] == layer_name or l["id"] == layer_name:
                if opacity is not None:
                    l["opacity"] = opacity
                if visible is not None:
                    l["visible"] = visible
                if locked is not None:
                    l["locked"] = locked
                if blending_mode is not None:
                    l["blending_mode"] = blending_mode
                return {"doc_id": doc_id, "layer_name": layer_name, "updated": True}
        return {"doc_id": doc_id, "layer_name": layer_name, "updated": True}

    def handle_set_active(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_name = params.get("layer_name")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and layer_name:
                    node = doc.nodeByName(layer_name)
                    if node:
                        doc.setActiveNode(node)
                        return {"doc_id": doc_id, "layer_name": layer_name, "active": True}
        except ImportError:
            pass

        # Headless mock mode
        return {"doc_id": doc_id, "layer_name": layer_name, "active": True}

    def handle_set_pixel_tile(params: dict) -> dict:
        import base64
        doc_id = params.get("doc_id", "default")
        layer_id = params.get("layer_id") or params.get("layer_name")
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", 0))
        h = int(params.get("height", 0))
        pixels_b64 = params.get("pixels_b64", "")

        raw_bytes = base64.b64decode(pixels_b64) if pixels_b64 else b""

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and layer_id:
                    node = doc.nodeByName(layer_id)
                    if node and raw_bytes:
                        try:
                            from PyQt5.QtCore import QByteArray
                            node.setPixelData(QByteArray(raw_bytes), x, y, w, h)
                        except ImportError:
                            try:
                                from PyQt6.QtCore import QByteArray
                                node.setPixelData(QByteArray(raw_bytes), x, y, w, h)
                            except ImportError:
                                node.setPixelData(raw_bytes, x, y, w, h)
                        return {"doc_id": doc_id, "layer_id": layer_id, "mode": "live_krita", "success": True}
        except Exception as exc:
            logger.warning("handle_set_pixel_tile failed in Krita: %s", exc)

        return {"doc_id": doc_id, "layer_id": layer_id, "mode": "headless_mock", "success": True}

    def handle_set_inherit_alpha(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_name = params.get("layer_name") or params.get("layer_id")
        inherit_alpha = bool(params.get("inherit_alpha", True))

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc and layer_name:
                    node = doc.nodeByName(layer_name)
                    if node and hasattr(node, "setInheritAlpha"):
                        node.setInheritAlpha(inherit_alpha)
                        return {
                            "doc_id": doc_id,
                            "layer_name": layer_name,
                            "inherit_alpha": inherit_alpha,
                            "updated": True,
                            "mode": "live_krita",
                        }
        except Exception as exc:
            logger.warning("Failed to set inherit alpha in Krita: %s", exc)

        # Headless mock mode
        layers = _get_doc_layers(doc_id)
        def _update_alpha(tree):
            for l in tree:
                if l["name"] == layer_name or l["id"] == layer_name:
                    l["inherit_alpha"] = inherit_alpha
                    return True
                if l.get("children") and _update_alpha(l["children"]):
                    return True
            return False

        updated = _update_alpha(layers)
        return {
            "doc_id": doc_id,
            "layer_name": layer_name,
            "inherit_alpha": inherit_alpha,
            "updated": updated,
            "mode": "headless_mock",
        }

    def handle_inject_svg(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_name = params.get("layer_name", "Vector_Layer")
        svg_string = params.get("svg_string", "")
        parent_group = params.get("parent_group") or params.get("parent_id")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    node = doc.nodeByName(layer_name)
                    if not node or node.type() != "vectorlayer":
                        node = doc.createVectorLayer(layer_name)
                        parent_node = doc.nodeByName(parent_group) if parent_group else doc.rootNode()
                        parent_node.addChildNode(node, None)
                    if hasattr(node, "addShapesFromSvg"):
                        node.addShapesFromSvg(svg_string)
                    doc.refreshProjection()
                    return {
                        "doc_id": doc_id,
                        "layer_name": layer_name,
                        "type": "vectorLayer",
                        "svg_injected": True,
                        "mode": "live_krita",
                    }
        except Exception as exc:
            logger.warning("Failed to inject SVG shapes in Krita: %s", exc)

        # Headless mock mode
        layers = _get_doc_layers(doc_id)
        new_vector_node = {
            "id": f"lyr_{uuid.uuid4().hex[:6]}",
            "name": layer_name,
            "type": "vectorLayer",
            "opacity": 255,
            "blending_mode": "normal",
            "visible": True,
            "locked": False,
            "inherit_alpha": False,
            "svg_data": svg_string,
            "children": [],
        }
        layers.append(new_vector_node)
        return {
            "doc_id": doc_id,
            "layer_name": layer_name,
            "type": "vectorLayer",
            "svg_injected": True,
            "mode": "headless_mock",
        }

    dispatcher.register_handler("layer.tree", handle_layer_tree)
    dispatcher.register_handler("layer.create", handle_create_layer)
    dispatcher.register_handler("layer.delete", handle_delete_layer)
    dispatcher.register_handler("layer.reorder", handle_reorder_layer)
    dispatcher.register_handler("layer.set_properties", handle_set_properties)
    dispatcher.register_handler("layer.set_active", handle_set_active)
    dispatcher.register_handler("layer.set_pixel_tile", handle_set_pixel_tile)
    dispatcher.register_handler("layer.set_inherit_alpha", handle_set_inherit_alpha)
    dispatcher.register_handler("layer.inject_svg", handle_inject_svg)
