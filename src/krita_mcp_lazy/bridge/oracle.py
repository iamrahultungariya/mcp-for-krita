"""Autonomous Bridge State Oracle for Krita MCP.

Proactively checks if Krita is running and listening on loopback port 18812,
and automatically extracts active canvas dimensions, layers, and document metadata
without requiring manual user input.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


@dataclass
class BridgeState:
    """Represents the live state of the Krita IPC connection and active canvas."""
    bridge_live: bool
    krita_running: bool
    port: int
    active_document: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BridgeStateOracle:
    """Probes the loopback transport and queries Krita's active GUI environment."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18812, token: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.token = token

    def is_socket_listening(self, timeout: float = 0.5) -> bool:
        """Check if TCP port is actively accepting connections."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            res = s.connect_ex((self.host, self.port))
            return res == 0
        except Exception as exc:
            logger.debug("Socket check failed: %s", exc)
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _query_active_doc_sync(self) -> Optional[Dict[str, Any]]:
        """Query active document metadata synchronously via temporary event loop."""
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._query_active_doc_async())
            finally:
                loop.close()
        except Exception as exc:
            logger.debug("Synchronous document query failed: %s", exc)
            return None

    async def _query_active_doc_async(self) -> Optional[Dict[str, Any]]:
        """Query active document metadata asynchronously."""
        client = AsyncIPCClient(host=self.host, port=self.port, token=self.token, timeout=2.0)
        try:
            await client.connect()
            res = await client.send_job("document.inspect_active", {})
            if res and res.result:
                return res.result
            # Fallback to document.inspect with doc_id=None
            res2 = await client.send_job("document.inspect", {})
            if res2 and res2.result and res2.result.get("doc_id") != "none":
                return res2.result
        except Exception as exc:
            logger.debug("Async active document query failed: %s", exc)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
        return None

    def probe(self, query_doc: bool = True) -> BridgeState:
        """Synchronously probe the Krita bridge state."""
        listening = self.is_socket_listening()
        if not listening:
            return BridgeState(
                bridge_live=False,
                krita_running=False,
                port=self.port,
                active_document=None,
                error="Krita IPC port 18812 is not accepting connections",
            )

        doc_info = None
        if query_doc:
            doc_info = self._query_active_doc_sync()

        return BridgeState(
            bridge_live=True,
            krita_running=True,
            port=self.port,
            active_document=doc_info,
        )

    async def probe_async(self, query_doc: bool = True) -> BridgeState:
        """Asynchronously probe the Krita bridge state."""
        listening = self.is_socket_listening()
        if not listening:
            return BridgeState(
                bridge_live=False,
                krita_running=False,
                port=self.port,
                active_document=None,
                error="Krita IPC port 18812 is not accepting connections",
            )

        doc_info = None
        if query_doc:
            doc_info = await self._query_active_doc_async()

        return BridgeState(
            bridge_live=True,
            krita_running=True,
            port=self.port,
            active_document=doc_info,
        )


_oracle_singleton: Optional[BridgeStateOracle] = None


def get_oracle(config: Optional[KritaConfig] = None) -> BridgeStateOracle:
    """Retrieve singleton instance of BridgeStateOracle."""
    global _oracle_singleton
    if _oracle_singleton is None:
        cfg = config or KritaConfig()
        _oracle_singleton = BridgeStateOracle(host=cfg.host, port=cfg.port, token=cfg.token)
    return _oracle_singleton
