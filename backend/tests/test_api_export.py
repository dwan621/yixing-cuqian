import httpx
import pytest
from app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _submit_and_wait(client):
    r = await client.post("/api/generate", json={
        "industry": "制造业", "scenario": "供应链管理", "scale": "500 人", "demo_minutes": 10
    })
    sid = r.json()["session_id"]
    import anyio
    for _ in range(50):
        await anyio.sleep(0.1)
        rr = await client.get(f"/api/result/{sid}")
        if rr.status_code == 200:
            return sid
    pytest.fail("pipeline did not finish")


async def test_export_markdown_returns_file(client):
    sid = await _submit_and_wait(client)
    resp = await client.get(f"/api/export/{sid}?format=md")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert len(resp.text) > 200


async def test_export_pdf_returns_501_in_mvp(client):
    sid = await _submit_and_wait(client)
    resp = await client.get(f"/api/export/{sid}?format=pdf")
    assert resp.status_code == 501
