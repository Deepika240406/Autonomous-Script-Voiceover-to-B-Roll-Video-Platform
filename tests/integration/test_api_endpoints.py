import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

        resp_ready = await client.get("/ready")
        assert resp_ready.status_code == 200
        assert resp_ready.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_create_job_and_idempotency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "script": "Trust is earned slowly.",
            "voice": "en-IN-female",
            "aspect_ratios": ["16:9"],
        }
        idempotency_key = "idemp-test-999"

        # 1. First submission -> HTTP 202
        resp1 = await client.post(
            "/api/v1/broll/jobs",
            json=payload,
            headers={"Idempotency-Key": idempotency_key}
        )
        assert resp1.status_code == 202
        data1 = resp1.json()
        assert "job_id" in data1
        assert data1["status"] == "queued"
        job_id = data1["job_id"]

        # 2. Second submission with same Idempotency-Key -> Returns same job without duplication
        resp2 = await client.post(
            "/api/v1/broll/jobs",
            json=payload,
            headers={"Idempotency-Key": idempotency_key}
        )
        assert resp2.status_code == 202
        data2 = resp2.json()
        assert data2["job_id"] == job_id

        # 3. GET /api/v1/jobs/{job_id}
        resp_status = await client.get(f"/api/v1/jobs/{job_id}")
        assert resp_status.status_code == 200
        assert resp_status.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_error_response_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit invalid payload (empty script and no audio)
        resp = await client.post("/api/v1/broll/jobs", json={"aspect_ratios": ["invalid_ratio"]})
        assert resp.status_code == 422
        err = resp.json()
        assert "error" in err
        assert "code" in err["error"]
        assert "message" in err["error"]
        assert "retryable" in err["error"]
        assert "details" in err["error"]
        assert err["error"]["code"] == "VALIDATION_ERROR"
