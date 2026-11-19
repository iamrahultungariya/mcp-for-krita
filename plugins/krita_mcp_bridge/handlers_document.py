"""Krita native API handlers for document operations executed on the main GUI thread."""

import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory document registry for active Krita instances and headless/mock environments
_doc_registry: Dict[str, Any] = {}
_mock_documents: Dict[str, dict] = {}


def get_document_by_id(doc_id: Optional[str] = None) -> Optional[Any]:
    """Retrieve KisDocument by ID or name from registry or Krita documents list.

    If doc_id is None or not found, safely falls back to Krita's activeDocument().
    """
    try:
        from krita import Krita
        app = Krita.instance()
        if not app:
            return None

        open_docs = app.documents() if hasattr(app, "documents") else []

        if doc_id and doc_id in _doc_registry:
            doc = _doc_registry[doc_id]
            if doc in open_docs:
                return doc
            else:
                del _doc_registry[doc_id]

        if doc_id:
            for d in open_docs:
                if getattr(d, "_lazy_id", None) == doc_id or d.fileName() == doc_id or d.name() == doc_id:
                    _doc_registry[doc_id] = d
                    return d

        return app.activeDocument()
    except ImportError:
        return None


def register_document_handlers(dispatcher: Any) -> None:
    """Register all document-related handlers with the main-thread dispatcher."""

    def handle_create_document(params: dict) -> dict:
        width = params.get("width", 1920)
        height = params.get("height", 1080)
        name = params.get("name", "Artwork")
        resolution_dpi = params.get("resolution_dpi", 300.0)
        color_model = params.get("color_model", "RGBA")
        bit_depth = params.get("bit_depth", "U8")
        color_profile = params.get("color_profile", "sRGB-elle-V2-srgbtrc.icc")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                cm = str(color_model).upper()
                bd = str(bit_depth).upper()
                prof = color_profile if color_profile else "sRGB-elle-V2-srgbtrc.icc"
                try:
                    def_prof = app.defaultColorProfile(cm, bd)
                    if def_prof:
                        prof = def_prof
                except Exception as pe:
                    pass

                import os, tempfile
                debug_log = os.path.join(tempfile.gettempdir(), "krita_mcp_bridge_debug.log")
                with open(debug_log, "a", encoding="utf-8") as f:
                    f.write(f"Calling app.createDocument({width}, {height}, {name}, {cm}, {bd}, {prof}, {resolution_dpi})\n")

                doc = app.createDocument(
                    int(width),
                    int(height),
                    str(name),
                    cm,
                    bd,
                    prof,
                    float(resolution_dpi),
                )
                with open(debug_log, "a", encoding="utf-8") as f:
                    f.write(f"app.createDocument returned: {doc}\n")

                if not doc:
                    raise RuntimeError("Krita app.createDocument returned None")
                active_win = app.activeWindow()
                if active_win:
                    active_win.addView(doc)
                doc_id = str(uuid.uuid4())[:8]
                doc._lazy_id = doc_id
                _doc_registry[doc_id] = doc
                return {
                    "doc_id": doc_id,
                    "name": doc.name(),
                    "width": doc.width(),
                    "height": doc.height(),
                    "resolution_dpi": doc.resolution(),
                    "color_model": doc.colorModel(),
                    "bit_depth": doc.colorDepth(),
                    "color_profile": doc.colorProfile(),
                    "modified": doc.modified(),
                }
        except Exception as e:
            import os, tempfile, traceback
            debug_log = os.path.join(tempfile.gettempdir(), "krita_mcp_bridge_debug.log")
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"Error in handle_create_document: {e}\n{traceback.format_exc()}\n")

        # Headless mock mode
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc_info = {
            "doc_id": doc_id,
            "name": name,
            "width": width,
            "height": height,
            "resolution_dpi": resolution_dpi,
            "color_model": color_model,
            "bit_depth": bit_depth,
            "color_profile": color_profile,
            "modified": False,
            "file_path": None,
            "layer_count": 1,
        }
        _mock_documents[doc_id] = doc_info
        return doc_info

    def handle_open_document(params: dict) -> dict:
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Parameter 'file_path' is required")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.openDocument(file_path)
                if not doc:
                    raise RuntimeError(f"Krita failed to open document at '{file_path}'")
                active_win = app.activeWindow()
                if active_win:
                    active_win.addView(doc)
                doc_id = str(uuid.uuid4())[:8]
                doc._lazy_id = doc_id
                _doc_registry[doc_id] = doc
                return {
                    "doc_id": doc_id,
                    "name": doc.name(),
                    "width": doc.width(),
                    "height": doc.height(),
                    "file_path": file_path,
                }
        except ImportError:
            pass

        # Headless mock mode
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc_info = {
            "doc_id": doc_id,
            "name": file_path.split("/")[-1].split("\\")[-1],
            "width": 1920,
            "height": 1080,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB-elle-V2-srgbtrc.icc",
            "file_path": file_path,
            "modified": False,
            "layer_count": 1,
        }
        _mock_documents[doc_id] = doc_info
        return doc_info

    def handle_save_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        file_path = params.get("file_path")
        export_format = params.get("export_format", "kra")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    if file_path:
                        success = doc.saveAs(file_path)
                    else:
                        success = doc.save()
                    return {"doc_id": doc_id or getattr(doc, "_lazy_id", "active"), "saved": success, "file_path": doc.fileName()}
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            _mock_documents[doc_id]["saved"] = True
            if file_path:
                _mock_documents[doc_id]["file_path"] = file_path
        return {"doc_id": doc_id, "saved": True, "file_path": file_path, "export_format": export_format}

    def handle_close_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    resolved_id = doc_id or getattr(doc, "_lazy_id", "active")
                    if doc_id and doc_id in _doc_registry:
                        del _doc_registry[doc_id]
                    for k, v in list(_doc_registry.items()):
                        if v == doc:
                            del _doc_registry[k]
                    closed = doc.close()
                    return {"doc_id": resolved_id, "closed": closed}
        except ImportError:
            pass

        # Headless mock mode
        if doc_id in _mock_documents:
            del _mock_documents[doc_id]
        return {"doc_id": doc_id, "closed": True}

    def handle_inspect_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    return {
                        "doc_id": doc_id or getattr(doc, "_lazy_id", "active"),
                        "name": doc.name(),
                        "width": doc.width(),
                        "height": doc.height(),
                        "resolution_dpi": doc.resolution(),
                        "color_model": doc.colorModel(),
                        "bit_depth": doc.colorDepth(),
                        "color_profile": doc.colorProfile(),
                        "modified": doc.modified(),
                    }
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            return _mock_documents[doc_id]
        if _mock_documents:
            return next(iter(_mock_documents.values()))
        return {
            "doc_id": doc_id or "none",
            "name": "Untitled",
            "width": 1920,
            "height": 1080,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB",
            "modified": False,
        }

    def handle_list_documents(params: dict) -> dict:
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                docs = app.documents()
                doc_list = []
                for idx, d in enumerate(docs):
                    did = getattr(d, "_lazy_id", None)
                    if not did:
                        did = f"doc_{idx}"
                        d._lazy_id = did
                        _doc_registry[did] = d
                    doc_list.append({
                        "doc_id": did,
                        "name": d.name(),
                        "width": d.width(),
                        "height": d.height(),
                        "modified": d.modified(),
                    })
                return {"documents": doc_list}
        except ImportError:
            pass

        # Headless mock mode
        return {"documents": list(_mock_documents.values())}

    def handle_refresh_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    doc.refreshProjection()
                    return {"doc_id": doc_id, "mode": "live_krita", "refreshed": True}
        except Exception:
            pass
        return {"doc_id": doc_id, "mode": "headless_mock", "refreshed": True}

    def handle_inspect_active(params: dict) -> dict:
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    did = getattr(doc, "_lazy_id", None)
                    if not did:
                        did = "active"
                        doc._lazy_id = did
                    active_node = doc.activeNode()
                    return {
                        "doc_id": did,
                        "name": doc.name(),
                        "file_name": doc.fileName(),
                        "width": doc.width(),
                        "height": doc.height(),
                        "resolution_dpi": doc.resolution(),
                        "color_model": doc.colorModel(),
                        "bit_depth": doc.colorDepth(),
                        "color_profile": doc.colorProfile(),
                        "modified": doc.modified(),
                        "active_layer": active_node.name() if active_node else None,
                        "mode": "live_krita",
                    }
        except Exception:
            pass
        if _mock_documents:
            first = next(iter(_mock_documents.values()))
            res = dict(first)
            res["mode"] = "headless_mock"
            return res
        return {
            "doc_id": "active",
            "name": "Untitled",
            "width": 1920,
            "height": 1080,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB",
            "mode": "headless_mock",
            "active_layer": "Paint Layer 1",
        }

    dispatcher.register_handler("document.create", handle_create_document)
    dispatcher.register_handler("document.open", handle_open_document)
    dispatcher.register_handler("document.save", handle_save_document)
    dispatcher.register_handler("document.close", handle_close_document)
    dispatcher.register_handler("document.inspect", handle_inspect_document)
    dispatcher.register_handler("document.inspect_active", handle_inspect_active)
    dispatcher.register_handler("document.list", handle_list_documents)
    dispatcher.register_handler("document.refresh", handle_refresh_document)
