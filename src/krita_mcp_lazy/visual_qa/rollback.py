"""Checkpoint snapshots and surgical rollback manager for reversible canvas mutations."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class CheckpointManager:
    """Manages creation, restoration, and listing of document mutation checkpoints."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def create_checkpoint(self, doc_id: str, label: str) -> Dict[str, Any]:
        """Save a snapshot of the current document state before destructive mutations."""
        payload = {"doc_id": doc_id, "label": label}
        resp = await self.client.send_job("checkpoint.create", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Checkpoint creation failed")

    async def rollback_checkpoint(self, doc_id: str, checkpoint_id: str) -> Dict[str, Any]:
        """Restore canvas state to a previously saved checkpoint snapshot."""
        payload = {"doc_id": doc_id, "checkpoint_id": checkpoint_id}
        resp = await self.client.send_job("checkpoint.rollback", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Checkpoint rollback failed")

    async def list_checkpoints(self, doc_id: str) -> List[Dict[str, Any]]:
        """List all active checkpoints recorded for a document."""
        payload = {"doc_id": doc_id}
        resp = await self.client.send_job("checkpoint.list", payload)
        res = check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Failed to list checkpoints")
        return res.get("checkpoints", []) if isinstance(res, dict) else []
