import json
import httpx
import pytest
from app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _payload(overrides=None):
    p = {"industry": "制造业", "scenario": "供应链管理", "scale": "500 人", "demo_minutes": 10}
    if overrides:
        p.update(overrides)
    return p


async def test_generate_returns_202_with_session_id(client):
    resp = await client.post("/api/generate", json=await _payload())
    assert resp.status_code == 202
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) >= 16


async def test_progress_returns_event_stream(client):
    r = await client.post("/api/generate", json=await _payload())
    sid = r.json()["session_id"]
    resp = await client.get(f"/api/progress/{sid}", timeout=30)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    events = [json.loads(line.removeprefix("data: ")) for line in lines if line.startswith("data:")]
    agents_seen = {ev["agent"] for ev in events if ev["status"] == "done"}
    assert "integrate" in agents_seen


async def test_result_returns_200_after_pipeline_done(client):
    r = await client.post("/api/generate", json=await _payload())
    sid = r.json()["session_id"]
    import anyio
    for _ in range(50):
        await anyio.sleep(0.1)
        rr = await client.get(f"/api/result/{sid}")
        if rr.status_code == 200:
            break
    else:
        pytest.fail("pipeline did not finish within 5s")
    data = rr.json()
    assert "markdown" in data
    assert "# 售前方案" in data["markdown"]


async def test_result_unknown_session_returns_404(client):
    resp = await client.get("/api/result/does-not-exist")
    assert resp.status_code == 404
