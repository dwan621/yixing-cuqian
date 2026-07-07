"""
E2E acceptance test — one test per AC-1..AC-7 (spec §6).

Run: pytest tests/test_e2e_ac.py -v
"""
import json
import time
import httpx
import pytest
from app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _submit(client, overrides=None):
    payload = {
        "industry": "制造业",
        "scenario": "供应链管理",
        "scale": "500 人",
        "demo_minutes": 10,
        **(overrides or {}),
    }
    r = await client.post("/api/generate", json=payload)
    assert r.status_code == 202, f"AC-1 submit failed: {r.text}"
    return r.json()["session_id"]


async def _wait(client, sid, timeout=30):
    """Poll /api/result until 200 or deadline."""
    deadline = time.monotonic() + timeout
    import anyio
    while time.monotonic() < deadline:
        await anyio.sleep(0.05)
        r = await client.get(f"/api/result/{sid}")
        if r.status_code == 200:
            return r.json()
    pytest.fail("AC-7: pipeline timed out")


# ── AC-1 ──────────────────────────────────────────────────────────────
async def test_ac1_submit_and_progress(client):
    """AC-1: 用户填写需求表单后能成功提交，系统进入 Agent 执行流程，前端显示执行进度."""
    r = await client.post(
        "/api/generate",
        json={
            "industry": "制造业",
            "scenario": "供应链管理",
            "scale": "500 人",
            "demo_minutes": 10,
        },
    )
    assert r.status_code == 202
    sid = r.json()["session_id"]
    resp = await client.get(f"/api/progress/{sid}", timeout=30)
    assert resp.status_code == 200
    assert "running" in resp.text or "done" in resp.text


# ── AC-2 ──────────────────────────────────────────────────────────────
async def test_ac2_parse_extracts_industry_scenario(client):
    """AC-2: 需求解析 Agent 能正确提取客户行业和关注场景."""
    sid = await _submit(client, {"industry": "金融", "scenario": "风控"})
    result = await _wait(client, sid)
    md = result["markdown"]
    assert "金融" in md or "finance" in md.lower()
    assert "风控" in md


# ── AC-3 ──────────────────────────────────────────────────────────────
async def test_ac3_at_least_three_features(client):
    """AC-3: 方案中包含与客户场景匹配的功能清单，功能点数量 >= 3 个."""
    sid = await _submit(client)
    result = await _wait(client, sid)
    functions = result["functions"]
    assert len(functions) >= 3, f"got {len(functions)}, need >= 3"


# ── AC-4 ──────────────────────────────────────────────────────────────
async def test_ac4_mock_data_fields_match_industry(client):
    """AC-4: 模拟数据与客户行业场景匹配，数据字段符合该行业的典型业务含义."""
    sid = await _submit(client, {"industry": "制造业", "scenario": "供应链管理"})
    result = await _wait(client, sid)
    tables = result["mock_data"]
    assert "orders" in tables, f"expected 'orders' table, got {list(tables.keys())}"
    first = tables["orders"][0]
    for field in ("order_id", "customer", "sku", "qty", "due_date", "status"):
        assert field in first, f"orders missing field '{field}'"


# ── AC-5 ──────────────────────────────────────────────────────────────
async def test_ac5_export_complete_file(client):
    """AC-5: 最终方案可导出为文件，导出文件包含完整内容且格式正确."""
    sid = await _submit(client)
    await _wait(client, sid)
    r = await client.get(f"/api/export/{sid}?format=md")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert len(r.text) > 500, f"export too short: {len(r.text)} chars"
    assert "# 售前方案" in r.text


# ── AC-6 ──────────────────────────────────────────────────────────────
async def test_ac6_failure_shows_agent_name_and_reason(client):
    """AC-6: Agent 执行失败时前端有明确提示，显示失败 Agent 名称和错误原因."""
    r = await client.post(
        "/api/generate",
        json={
            "industry": "不存在的行业XYZ",
            "scenario": "测试",
            "scale": "1 人",
            "demo_minutes": 5,
        },
    )
    sid = r.json()["session_id"]
    resp = await client.get(f"/api/progress/{sid}", timeout=30)
    text = resp.text
    lines = [
        line.removeprefix("data: ")
        for line in text.strip().split("\n")
        if line.startswith("data:")
    ]
    events = [json.loads(line) for line in lines]
    failed = [
        ev for ev in events
        if ev.get("status") == "failed" or ev.get("error")
    ]
    assert failed, "must have a failed event for invalid industry"
    error_text = str(failed[0])
    assert "parse" in error_text or "unknown" in error_text.lower(), (
        f"must name failing agent: {error_text}"
    )


# ── AC-7 ──────────────────────────────────────────────────────────────
async def test_ac7_end_to_end_within_30_seconds(client):
    """AC-7: 从提交到结果展示的端到端耗时 <= 30 秒."""
    start = time.monotonic()
    sid = await _submit(client)
    await _wait(client, sid, timeout=30)
    elapsed = time.monotonic() - start
    assert elapsed <= 30, f"AC-7 failed: {elapsed:.1f}s > 30s"
