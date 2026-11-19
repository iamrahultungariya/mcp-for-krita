"""Unit tests for BridgeStateOracle."""

import pytest
from unittest.mock import patch, MagicMock
from krita_mcp_lazy.bridge.oracle import BridgeStateOracle, BridgeState


def test_oracle_reports_disconnected_when_port_closed():
    oracle = BridgeStateOracle(host="127.0.0.1", port=19999)
    state = oracle.probe()
    assert state.bridge_live is False
    assert state.active_document is None


def test_oracle_reports_live_when_port_open():
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        oracle = BridgeStateOracle(host="127.0.0.1", port=port)
        state = oracle.probe(query_doc=False)
        assert state.bridge_live is True
    finally:
        srv.close()


def test_oracle_auto_senses_active_document():
    oracle = BridgeStateOracle(host="127.0.0.1", port=18812)
    mock_doc = {"doc_id": "active", "name": "running.kra", "width": 3840, "height": 2160, "resolution_dpi": 300.0}
    with patch.object(oracle, "_query_active_doc_sync", return_value=mock_doc):
        with patch.object(oracle, "is_socket_listening", return_value=True):
            state = oracle.probe(query_doc=True)
            assert state.bridge_live is True
            assert state.active_document is not None
            assert state.active_document["name"] == "running.kra"
            assert state.active_document["width"] == 3840
