import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.core.errors import KritaError, ErrorCode
from krita_mcp_lazy.core.security import AuthTokenManager, get_or_create_shared_token
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus


def test_shared_token_env_var(monkeypatch):
    test_token = "env_secret_token_1234567890abcdef"
    monkeypatch.setenv("KRITA_MCP_TOKEN", test_token)
    token = get_or_create_shared_token()
    assert token == test_token

    # Ensure KritaConfig picks it up by default
    config = KritaConfig()
    assert config.token == test_token


def test_shared_token_file_persistence(monkeypatch, tmp_path):
    monkeypatch.delenv("KRITA_MCP_TOKEN", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    token1 = get_or_create_shared_token()
    assert len(token1) >= 32
    token_file = fake_home / ".krita_mcp_lazy" / "session.token"
    assert token_file.exists()
    assert token_file.read_text(encoding="utf-8").strip() == token1

    # Second call should read the existing token file
    token2 = get_or_create_shared_token()
    assert token2 == token1


def test_config_defaults():
    config = KritaConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 18812
    assert config.queue_max_size == 100
    assert config.socket_timeout == 30.0
    assert config.max_payload_size == 32 * 1024 * 1024


def test_config_loopback_enforcement():
    # Only loopback addresses are allowed for security
    KritaConfig(host="127.0.0.1")
    KritaConfig(host="localhost")
    
    with pytest.raises(ValidationError):
        KritaConfig(host="0.0.0.0")
        
    with pytest.raises(ValidationError):
        KritaConfig(host="192.168.1.100")


def test_auth_token_lifecycle():
    mgr = AuthTokenManager()
    token = mgr.generate_token()
    assert len(token) >= 32
    assert mgr.validate_token(token) is True
    assert mgr.validate_token("invalid_token") is False
    assert mgr.validate_token("") is False
    assert mgr.validate_token(None) is False
    
    # Revocation
    mgr.revoke_token()
    assert mgr.get_token() is None
    assert mgr.validate_token(token) is False


def test_auth_token_custom_initialization():
    custom_token = "my_custom_secret_token_1234567890abcdef"
    mgr = AuthTokenManager(token=custom_token)
    assert mgr.get_token() == custom_token
    assert mgr.validate_token(custom_token) is True
    assert mgr.validate_token("forged_token") is False


def test_job_schemas():
    req = JobRequest(action="document.create", params={"width": 1920, "height": 1080})
    assert req.job_id is not None
    assert len(req.job_id) > 0
    assert req.action == "document.create"
    assert req.params == {"width": 1920, "height": 1080}
    assert req.created_at > 0

    resp = JobResponse(
        job_id=req.job_id,
        status=JobStatus.SUCCESS,
        result={"doc_id": "doc_1"},
        elapsed_ms=12.5,
    )
    assert resp.status == JobStatus.SUCCESS
    assert resp.result == {"doc_id": "doc_1"}
    assert resp.error is None
    assert resp.elapsed_ms == 12.5

    # Check serialization round-trip
    req_json = req.model_dump_json()
    deserialized_req = JobRequest.model_validate_json(req_json)
    assert deserialized_req.job_id == req.job_id
    assert deserialized_req.action == req.action


def test_job_error_response():
    resp = JobResponse(
        job_id="job-err-1",
        status=JobStatus.FAILED,
        error="Document creation failed",
        error_code=ErrorCode.DOCUMENT_ERROR.value,
    )
    assert resp.status == JobStatus.FAILED
    assert resp.error == "Document creation failed"
    assert resp.error_code == ErrorCode.DOCUMENT_ERROR.value


def test_krita_error_taxonomy():
    err = KritaError(
        code=ErrorCode.AUTH_FAILED,
        message="Authentication failed: invalid token",
        details={"attempted_host": "127.0.0.1"},
        job_id="job-123",
    )
    assert err.code == ErrorCode.AUTH_FAILED
    assert err.message == "Authentication failed: invalid token"
    assert err.job_id == "job-123"
    assert "AUTH_FAILED" in str(err)
    assert "Authentication failed" in str(err)
    
    err_dict = err.to_dict()
    assert err_dict["code"] == "AUTH_FAILED"
    assert err_dict["message"] == "Authentication failed: invalid token"
    assert err_dict["details"] == {"attempted_host": "127.0.0.1"}
    assert err_dict["job_id"] == "job-123"


def test_schema_dataclass_fallback_parity():
    from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
    req = JobRequest(action="test.ping", params={"val": 42})
    dumped = req.model_dump()
    assert dumped["action"] == "test.ping"
    assert dumped["params"] == {"val": 42}
    validated = JobRequest.model_validate(dumped)
    assert validated.action == "test.ping"
    assert validated.params == {"val": 42}

    resp = JobResponse(job_id=req.job_id, status=JobStatus.SUCCESS, result={"pong": True})
    dumped_resp = resp.model_dump()
    assert dumped_resp["job_id"] == req.job_id
    assert dumped_resp["status"] == "SUCCESS"
    assert dumped_resp["result"] == {"pong": True}
    validated_resp = JobResponse.model_validate(dumped_resp)
    assert validated_resp.job_id == req.job_id
    assert validated_resp.status == JobStatus.SUCCESS

