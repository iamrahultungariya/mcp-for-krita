"""Verify live loopback IPC connectivity with Krita bridge extension."""

import asyncio
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from krita_mcp_lazy.core.security import get_or_create_shared_token
from krita_mcp_lazy.transport.client import AsyncIPCClient


async def main() -> None:
    token = get_or_create_shared_token()
    print(f"Connecting to Krita bridge on 127.0.0.1:18812 with token {token[:8]}...")
    client = AsyncIPCClient(host="127.0.0.1", port=18812, token=token, timeout=5.0)

    try:
        await client.connect()
        print("TCP handshake authenticated successfully!")

        res_ping = await client.send_job("ping", {})
        print("PING RESPONSE:", res_ping.result)
        assert res_ping.result.get("pong") is True, f"Unexpected ping result: {res_ping.result}"

        res_ver = await client.send_job("system.version", {})
        print("LIVE_KRITA_CONNECTED:", res_ver.result)
        assert res_ver.result.get("engine") == "krita-MCP-lazy", f"Unexpected version result: {res_ver.result}"

        print("SUCCESS: Live Krita bridge verified and ready for production jobs.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
