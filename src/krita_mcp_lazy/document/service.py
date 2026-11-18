"""Document service orchestrating high-level document lifecycle operations."""

import logging
from typing import Any, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.document.models import DocumentSpec
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


class DocumentService:
    """Provides high-level document CRUD and inspection operations over loopback IPC."""

    def __init__(self, client: AsyncIPCClient) -> None:
        self.client = client

    def _ensure_success(self, resp: Any, default_message: str) -> dict[str, Any]:
        """Validate response status or raise KritaError with proper taxonomy code."""
        if resp.status != JobStatus.SUCCESS:
            code = ErrorCode.DOCUMENT_ERROR
            if resp.error_code:
                for member in ErrorCode:
                    if member.value == resp.error_code:
                        code = member
                        break
            raise KritaError(
                code=code,
                message=resp.error or default_message,
                job_id=resp.job_id,
            )
        return resp.result or {}

    async def create_document(self, spec: DocumentSpec) -> dict[str, Any]:
        """Create a new document with specified dimensions, color profile, and bit depth."""
        req = JobRequest(action="document.create", params=spec.model_dump())
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to create document")

    async def open_document(self, file_path: str) -> dict[str, Any]:
        """Open an existing .kra or supported image document into Krita."""
        req = JobRequest(action="document.open", params={"file_path": file_path})
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to open document from '{file_path}'")

    async def save_document(
        self,
        doc_id: str,
        file_path: Optional[str] = None,
        export_format: Optional[str] = "kra",
    ) -> dict[str, Any]:
        """Save open document to disk as native .kra or export to target format."""
        params = {"doc_id": doc_id, "file_path": file_path, "export_format": export_format}
        req = JobRequest(action="document.save", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to save document '{doc_id}'")

    async def close_document(self, doc_id: str, force: bool = False) -> dict[str, Any]:
        """Close an open document, verifying unsaved state unless force is True."""
        req = JobRequest(action="document.close", params={"doc_id": doc_id, "force": force})
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to close document '{doc_id}'")

    async def inspect_document(self, doc_id: Optional[str] = None) -> dict[str, Any]:
        """Inspect active or specified document attributes, layers count, and dimensions."""
        params = {"doc_id": doc_id} if doc_id else {}
        req = JobRequest(action="document.inspect", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to inspect document")

    async def list_documents(self) -> List[dict[str, Any]]:
        """List all currently open documents in the active Krita instance."""
        req = JobRequest(action="document.list", params={})
        resp = await self.client.send_job(req)
        result = self._ensure_success(resp, "Failed to list documents")
        return result.get("documents", [])
