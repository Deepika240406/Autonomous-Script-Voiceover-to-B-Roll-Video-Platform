import pytest
from app.core.security import is_safe_url
from app.core.exceptions import SSRException
from app.core.idempotency import IdempotencyStore


def test_ssrf_rejection():
    # Loopback
    with pytest.raises(SSRException):
        is_safe_url("http://127.0.0.1:8000/internal", allow_local_for_dev=False)

    # Private network
    with pytest.raises(SSRException):
        is_safe_url("http://192.168.1.1/admin", allow_local_for_dev=False)

    # Cloud metadata endpoint
    with pytest.raises(SSRException):
        is_safe_url("http://169.254.169.254/latest/meta-data/", allow_local_for_dev=False)

    # Invalid scheme
    with pytest.raises(SSRException):
        is_safe_url("ftp://example.com/file.mp3", allow_local_for_dev=False)


def test_idempotency_store():
    store = IdempotencyStore(ttl_seconds=60)
    key = "test-key-123"
    req_hash = store.compute_hash({"script": "example narration"})

    assert store.get(key) is None

    store.set(key, "job-abc", req_hash, {"status": "queued", "job_id": "job-abc"})
    cached = store.get(key)
    assert cached is not None
    assert cached["job_id"] == "job-abc"
    assert cached["request_hash"] == req_hash
