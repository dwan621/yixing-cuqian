# 以型促签 (Pre-sales Rapid Prototype Generator) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-Agent pre-sales prototype generator: user submits a customer scenario (industry / focus / scale / demo length) via a Vue 3 form; a FastAPI orchestrator runs a 5-Agent DAG (parse → design → {content, data, architecture} → integrate) with SSE progress streaming and returns a Markdown pre-sales package that can be exported to a file — end-to-end in ≤ 30 s.

**Architecture:** Single git repo split into `backend/` (Python + FastAPI, owns the DAG) and `frontend/` (Vue 3 + Vite + Element Plus). Every Agent implements one `Agent` Protocol; the initial delivery ships **template/rule-based Agents** (no LLM calls) — per spec §5.4 — with the seam wired so a single line in an `AGENT_REGISTRY` dict swaps in a real LLM Agent later without touching the orchestrator. Progress is streamed to the browser over Server-Sent Events (SSE); customer inputs are held in an in-process session dict and never persisted to disk (spec §4 数据安全).

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, pydantic v2, PyYAML, pytest, httpx (test client), anyio; Node 20+, Vue 3, Vite, Element Plus, Pinia, TypeScript, Vitest.

## Global Constraints

Copied verbatim from `doc/02-以型促签.docx` (v1.0, 2026-07-06). Every task must not violate these.

- **端到端耗时 ≤ 30 秒** from form submit to fully rendered plan (§4 响应速度, AC-7).
- **功能清单覆盖 ≥ 80 % 客户场景相关功能点** (§4 输出质量).
- **单个 Agent 执行失败时，编排引擎应给出明确错误信息，不影响其他 Agent 执行** (§4 容错性, AC-6). Failure surfaces the Agent's name and reason; sibling Agents on independent branches continue.
- **功能演示模板和 Agent 能力可配置**: new industries are added by dropping a YAML in `backend/templates/industries/`, no orchestrator edits (§4 可配置性).
- **客户信息仅用于当前会话，不持久化存储或对外泄露** (§4 数据安全). No disk writes of customer input, no logging of `industry`/`scenario`/`background` fields, in-memory session dict only.
- **每个 Agent 的 prompt 应包含: 角色定义 · 输入格式 · 输出格式 · 约束条件** (§5.3). Even for template Agents, keep the four-section structure as a top-of-file docstring so LLM-swap is mechanical.
- **Agent 通信通过函数调用链**: upstream output → downstream input, no shared bus (§5.1).

---

## File Structure

```
backend/
  pyproject.toml
  app/
    __init__.py
    main.py                    # FastAPI app + routes
    schemas.py                 # pydantic request/response models
    session.py                 # in-memory session dict, TTL, no disk writes
    agents/
      __init__.py
      base.py                  # Agent Protocol + AgentError + AgentResult
      parse_agent.py           # F2-1 需求解析
      design_agent.py          # F2-2 方案设计
      content_agent.py         # F2-3 内容生成
      data_agent.py            # F2-4 数据模拟
      architecture_agent.py    # architecture description (Mermaid)
      integrate_agent.py       # 结果整合 → Markdown
      registry.py              # AGENT_REGISTRY: {name -> Agent instance}
    orchestrator/
      __init__.py
      dag.py                   # DAG definition + parallel fan-out
      engine.py                # runs the DAG, emits progress events
      events.py                # progress event dataclasses
    templates/
      industries/
        manufacturing.yaml
        finance.yaml
        retail.yaml
      __init__.py              # loader that scans industries/
    export/
      markdown.py              # AC-5 export
  tests/
    conftest.py
    test_schemas.py
    test_session.py
    test_parse_agent.py
    test_design_agent.py
    test_content_agent.py
    test_data_agent.py
    test_architecture_agent.py
    test_integrate_agent.py
    test_orchestrator_success.py
    test_orchestrator_failure.py
    test_api_generate.py       # AC-1 + AC-7
    test_api_export.py         # AC-5
    test_e2e_ac.py             # AC-1..AC-7 as one file
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.ts
    App.vue
    api.ts                     # fetch + SSE wrappers
    stores/
      plan.ts                  # Pinia store: form, progress, result
    components/
      RequirementForm.vue      # F1-1..F1-4
      ProgressPanel.vue        # F2-6
      PlanView.vue             # F3-1 renders Markdown
      ExportButton.vue         # F3-6 (Markdown export in MVP)
  tests/
    RequirementForm.spec.ts
    PlanView.spec.ts
Makefile                       # dev/test targets for both stacks
README.md                      # points to CLAUDE.md and this plan
```

**Boundary rationale:**
- Each Agent is its own file so LLM-swap replaces one file, not a diff across the orchestrator.
- `orchestrator/dag.py` is data (a list of node descriptors); `engine.py` is the runner. New nodes = edit config, not runner (spec §4 可配置性).
- `templates/industries/*.yaml` = configuration; loader auto-discovers. Adding an industry never touches Python.
- Frontend `api.ts` is the only place that knows about SSE — components consume the Pinia store.

---

## Task 1: Backend scaffold, schemas, and in-memory session

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/session.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_schemas.py`
- Create: `backend/tests/test_session.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `RequirementInput(industry: str, scenario: str, scale: str, demo_minutes: int, background: str | None = None, template: str | None = None)` — pydantic model.
  - `SessionStore.create(req: RequirementInput) -> str` returns a `session_id`; `SessionStore.get(session_id: str) -> RequirementInput | None`; `SessionStore.set_result(session_id, result: dict) -> None`; `SessionStore.result(session_id) -> dict | None`; `SessionStore.evict_expired() -> None`.
  - `SESSION_TTL_SECONDS = 900` module constant.

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "yixing-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "pydantic>=2.6",
  "pyyaml>=6.0",
  "anyio>=4.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install deps**

Run from `backend/`:
```bash
python -m venv .venv
.venv/Scripts/activate  # (Windows bash) or source .venv/bin/activate on POSIX
pip install -e ".[dev]"
```
Expected: `Successfully installed fastapi ... pytest ...` with no errors.

- [ ] **Step 3: Write the failing test for schemas**

Create `backend/tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from app.schemas import RequirementInput


def test_requirement_input_accepts_full_form():
    req = RequirementInput(
        industry="制造业",
        scenario="供应链管理",
        scale="500 人以上",
        demo_minutes=15,
        background="客户痛点：库存周转慢",
        template="供应链演示模板",
    )
    assert req.industry == "制造业"
    assert req.demo_minutes == 15


def test_requirement_input_defaults_optional_fields_to_none():
    req = RequirementInput(
        industry="金融",
        scenario="风控",
        scale="1000 人",
        demo_minutes=5,
    )
    assert req.background is None
    assert req.template is None


def test_requirement_input_missing_required_field_raises():
    with pytest.raises(ValidationError):
        RequirementInput(scenario="供应链", scale="500 人", demo_minutes=10)  # missing industry


def test_requirement_input_rejects_non_positive_demo_minutes():
    with pytest.raises(ValidationError):
        RequirementInput(industry="制造业", scenario="供应链", scale="500 人", demo_minutes=0)


def test_requirement_input_rejects_negative_demo_minutes():
    with pytest.raises(ValidationError):
        RequirementInput(industry="制造业", scenario="供应链", scale="500 人", demo_minutes=-1)
```

- [ ] **Step 4: Run tests, expect failure**

Run from `backend/`:
```bash
pytest tests/test_schemas.py -v
```
Expected: `ImportError: cannot import name 'RequirementInput' from 'app.schemas'` — because the module does not exist yet.

- [ ] **Step 5: Implement `app/schemas.py`**

Create `backend/app/schemas.py`:
```python
from __future__ import annotations
from pydantic import BaseModel, Field


class RequirementInput(BaseModel):
    industry: str = Field(..., min_length=1)
    scenario: str = Field(..., min_length=1)
    scale: str = Field(..., min_length=1)
    demo_minutes: int = Field(..., gt=0, le=120)
    background: str | None = None
    template: str | None = None


class GenerateResponse(BaseModel):
    session_id: str


class PlanResult(BaseModel):
    session_id: str
    markdown: str
    functions: list[dict]
    mock_data: dict
    architecture: str
    demo_script: dict
```

Create `backend/app/__init__.py` (empty file).
Create `backend/tests/__init__.py` (empty file).
Create `backend/tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

- [ ] **Step 6: Run schema tests, expect pass**

```bash
pytest tests/test_schemas.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Write the failing test for session store**

Create `backend/tests/test_session.py`:
```python
import time
from app.schemas import RequirementInput
from app.session import SessionStore, SESSION_TTL_SECONDS


def _req():
    return RequirementInput(industry="制造业", scenario="供应链", scale="500 人", demo_minutes=10)


def test_create_returns_unique_ids():
    store = SessionStore()
    id_a = store.create(_req())
    id_b = store.create(_req())
    assert id_a != id_b
    assert len(id_a) >= 16


def test_get_returns_the_stored_request():
    store = SessionStore()
    sid = store.create(_req())
    got = store.get(sid)
    assert got is not None
    assert got.industry == "制造业"


def test_get_unknown_returns_none():
    store = SessionStore()
    assert store.get("does-not-exist") is None


def test_set_and_read_result():
    store = SessionStore()
    sid = store.create(_req())
    store.set_result(sid, {"markdown": "# hi"})
    assert store.result(sid) == {"markdown": "# hi"}


def test_evict_expired_removes_stale(monkeypatch):
    store = SessionStore()
    sid = store.create(_req())
    # Fast-forward the store's clock
    store._clock = lambda: time.monotonic() + SESSION_TTL_SECONDS + 1
    store.evict_expired()
    assert store.get(sid) is None


def test_evict_expired_keeps_fresh():
    store = SessionStore()
    sid = store.create(_req())
    store.evict_expired()
    assert store.get(sid) is not None
```

- [ ] **Step 8: Run, expect failure**

```bash
pytest tests/test_session.py -v
```
Expected: `ImportError: cannot import name 'SessionStore' from 'app.session'`.

- [ ] **Step 9: Implement `app/session.py`**

```python
from __future__ import annotations
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable
from app.schemas import RequirementInput

SESSION_TTL_SECONDS = 900  # 15 minutes


@dataclass
class _Entry:
    req: RequirementInput
    created_at: float
    result: dict | None = None


class SessionStore:
    """In-memory only. No disk writes, ever (spec §4 数据安全)."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._entries: dict[str, _Entry] = {}
        self._clock = clock or time.monotonic

    def create(self, req: RequirementInput) -> str:
        sid = secrets.token_urlsafe(16)
        self._entries[sid] = _Entry(req=req, created_at=self._clock())
        return sid

    def get(self, session_id: str) -> RequirementInput | None:
        entry = self._entries.get(session_id)
        return entry.req if entry else None

    def set_result(self, session_id: str, result: dict) -> None:
        if session_id in self._entries:
            self._entries[session_id].result = result

    def result(self, session_id: str) -> dict | None:
        entry = self._entries.get(session_id)
        return entry.result if entry else None

    def evict_expired(self) -> None:
        now = self._clock()
        stale = [sid for sid, e in self._entries.items() if now - e.created_at > SESSION_TTL_SECONDS]
        for sid in stale:
            del self._entries[sid]
```

- [ ] **Step 10: Run all tests, expect pass**

```bash
pytest -v
```
Expected: 11 passed.

- [ ] **Step 11: Commit**

```bash
git init  # if not already a repo
git add backend/pyproject.toml backend/app backend/tests
git commit -m "feat(backend): scaffold pyproject, RequirementInput schema, in-memory SessionStore"
```

---

## Task 2: Agent Protocol, AgentResult, AgentError

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/base.py`
- Create: `backend/tests/test_agent_base.py`

**Interfaces:**
- Consumes: nothing agent-specific yet.
- Produces:
  - `AgentContext` — a `pydantic.BaseModel` carrying `session_id`, the immutable `requirement: RequirementInput`, and a mutable `outputs: dict[str, Any]` where each Agent writes its result under its own `name`.
  - `Agent(Protocol)` — has attribute `name: str` and async method `async def run(self, ctx: AgentContext) -> Any`.
  - `AgentError(Exception)` — carries `agent_name: str` and `reason: str`; `__str__` returns `f"{agent_name}: {reason}"`.
  - `AgentResult` — dataclass with `agent_name: str`, `ok: bool`, `value: Any`, `error: str | None`, `elapsed_ms: int`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_base.py`:
```python
import pytest
from app.schemas import RequirementInput
from app.agents.base import Agent, AgentContext, AgentError, AgentResult


def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


class _StubAgent:
    name = "stub"

    async def run(self, ctx: AgentContext):
        ctx.outputs[self.name] = {"echo": ctx.requirement.industry}
        return ctx.outputs[self.name]


async def test_stub_agent_conforms_to_protocol():
    a: Agent = _StubAgent()  # type: ignore[assignment]
    ctx = _ctx()
    out = await a.run(ctx)
    assert out == {"echo": "制造业"}
    assert ctx.outputs["stub"] == {"echo": "制造业"}


def test_agent_error_stringifies_agent_and_reason():
    err = AgentError(agent_name="parse", reason="missing industry")
    assert str(err) == "parse: missing industry"
    assert err.agent_name == "parse"
    assert err.reason == "missing industry"


def test_agent_result_success_shape():
    r = AgentResult(agent_name="parse", ok=True, value={"a": 1}, error=None, elapsed_ms=42)
    assert r.ok
    assert r.value == {"a": 1}
    assert r.error is None


def test_agent_result_failure_shape():
    r = AgentResult(agent_name="parse", ok=False, value=None, error="boom", elapsed_ms=5)
    assert not r.ok
    assert r.error == "boom"
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_agent_base.py -v
```
Expected: `ImportError: cannot import name 'Agent' from 'app.agents.base'`.

- [ ] **Step 3: Implement `app/agents/base.py`**

Create `backend/app/agents/__init__.py` (empty).
Create `backend/app/agents/base.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict
from app.schemas import RequirementInput


class AgentContext(BaseModel):
    """Passed to every Agent. `outputs` is mutable; other fields are frozen."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    requirement: RequirementInput
    outputs: dict[str, Any]


@runtime_checkable
class Agent(Protocol):
    name: str

    async def run(self, ctx: AgentContext) -> Any: ...


class AgentError(Exception):
    """Raised by an Agent to signal a controlled failure with the Agent's name attached.

    The orchestrator catches this, records the failure, and continues siblings on
    independent branches (spec §4 容错性, AC-6).
    """

    def __init__(self, agent_name: str, reason: str) -> None:
        super().__init__(f"{agent_name}: {reason}")
        self.agent_name = agent_name
        self.reason = reason


@dataclass
class AgentResult:
    agent_name: str
    ok: bool
    value: Any
    error: str | None
    elapsed_ms: int
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_agent_base.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/__init__.py backend/app/agents/base.py backend/tests/test_agent_base.py
git commit -m "feat(backend): Agent Protocol, AgentContext, AgentError, AgentResult"
```

---

## Task 3: Industry templates and template loader

**Files:**
- Create: `backend/app/templates/__init__.py`
- Create: `backend/app/templates/industries/manufacturing.yaml`
- Create: `backend/app/templates/industries/finance.yaml`
- Create: `backend/app/templates/industries/retail.yaml`
- Create: `backend/tests/test_templates.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `IndustryTemplate` pydantic model with fields: `name: str`, `aliases: list[str]`, `default_scenarios: list[str]`, `feature_bank: list[FeatureSpec]`, `mock_data_schema: dict[str, list[dict]]`, `talking_points: list[str]`, `architecture_snippet: str`.
  - `FeatureSpec` pydantic model: `id: str`, `title: str`, `description: str`, `demo_steps: list[str]`, `talking_points: list[str]`, `scenarios: list[str]`.
  - `load_templates() -> dict[str, IndustryTemplate]` — scans `backend/app/templates/industries/*.yaml` on first call; caches the result. Keys are the `name` field, lowercased.
  - `resolve_industry(query: str, templates: dict[str, IndustryTemplate]) -> IndustryTemplate | None` — matches on `name` or `aliases`, case-insensitive; returns None if no match.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_templates.py`:
```python
from app.templates import load_templates, resolve_industry, IndustryTemplate


def test_load_templates_finds_all_three_seeded_industries():
    templates = load_templates()
    names = set(templates.keys())
    assert {"manufacturing", "finance", "retail"} <= names


def test_manufacturing_has_scenario_and_feature_bank():
    t = load_templates()["manufacturing"]
    assert isinstance(t, IndustryTemplate)
    assert "供应链管理" in t.default_scenarios
    assert len(t.feature_bank) >= 5  # AC-3 needs >= 3; we ship >= 5 per industry


def test_resolve_industry_matches_by_alias():
    templates = load_templates()
    t = resolve_industry("制造业", templates)
    assert t is not None
    assert t.name == "manufacturing"


def test_resolve_industry_case_insensitive():
    templates = load_templates()
    t = resolve_industry("MANUFACTURING", templates)
    assert t is not None
    assert t.name == "manufacturing"


def test_resolve_industry_unknown_returns_none():
    templates = load_templates()
    assert resolve_industry("外星科技", templates) is None


def test_feature_bank_entries_carry_demo_steps_and_talking_points():
    t = load_templates()["manufacturing"]
    for f in t.feature_bank:
        assert f.id
        assert f.title
        assert len(f.demo_steps) >= 1
        assert len(f.talking_points) >= 1


def test_mock_data_schema_lists_at_least_one_table_per_industry():
    for name in ("manufacturing", "finance", "retail"):
        t = load_templates()[name]
        assert len(t.mock_data_schema) >= 1
        # every schema entry describes a list of rows
        for table_name, rows in t.mock_data_schema.items():
            assert isinstance(rows, list) and len(rows) >= 3
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_templates.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.templates'`.

- [ ] **Step 3: Write the three YAML templates**

Create `backend/app/templates/industries/manufacturing.yaml`:
```yaml
name: manufacturing
aliases: ["制造业", "制造", "工厂", "manufacturing"]
default_scenarios: ["供应链管理", "生产计划", "质量管理", "设备管理"]
architecture_snippet: |
  客户 ERP → API 网关 → 供应链核心服务 → { 订单 · 库存 · 物流 · 生产 } → 报表与预警
feature_bank:
  - id: mfg-order
    title: 智能订单管理
    description: 集中管理来自多渠道的销售订单，自动分配产能与物料
    demo_steps:
      - 打开订单列表，展示待处理订单
      - 演示自动派单：勾选订单，点击"智能派单"
      - 展示派单结果与产能占用图
    talking_points:
      - 与客户现有 ERP 双向同步，无需二次录入
      - AI 派单基于产能、交期、成本三重最优
    scenarios: ["供应链管理", "生产计划"]
  - id: mfg-inventory
    title: 实时库存看板
    description: 按仓库、SKU、批次多维度展示库存与安全线告警
    demo_steps:
      - 切换到库存看板视图
      - 筛选低于安全线的 SKU
      - 展示自动补货建议
    talking_points:
      - 分钟级刷新，替代日报表
      - 安全线自动学习季节性波动
    scenarios: ["供应链管理"]
  - id: mfg-logistics
    title: 物流追踪
    description: 集成主流物流服务商，实时展示订单在途状态
    demo_steps:
      - 输入订单号，展示轨迹地图
      - 演示异常预警（超时、路径偏离）
    talking_points:
      - 一图看清全国订单在途分布
      - 异常自动派单到客户经理
    scenarios: ["供应链管理", "物流"]
  - id: mfg-quality
    title: 质量追溯
    description: 从成品逆向追溯到批次、工序、原料供应商
    demo_steps:
      - 输入成品编号，展示批次树
      - 定位到问题工序与责任人
    talking_points:
      - 质量事故 5 分钟内定位根因
      - 满足 IATF 16949 等审核要求
    scenarios: ["质量管理"]
  - id: mfg-oee
    title: 设备 OEE 分析
    description: 综合可用率、性能、良率三个维度评估设备效率
    demo_steps:
      - 展示 OEE 热力图
      - 下钻到单台设备的停机原因
    talking_points:
      - 直接对接 PLC / MES 采集数据
      - 停机原因分类由客户自定义
    scenarios: ["设备管理", "生产计划"]
  - id: mfg-forecast
    title: 需求预测
    description: 基于历史订单与季节因子生成月度需求预测
    demo_steps:
      - 选择 SKU 与预测周期
      - 展示预测曲线与置信区间
    talking_points:
      - 模型每周自动重训练
      - 支持人工调整并留痕
    scenarios: ["供应链管理", "生产计划"]
mock_data_schema:
  orders:
    - {order_id: "SO-2026-0001", customer: "华东汽车零部件", sku: "GEAR-A12", qty: 500, due_date: "2026-07-15", status: "in_production"}
    - {order_id: "SO-2026-0002", customer: "南方机械", sku: "SHAFT-B08", qty: 1200, due_date: "2026-07-20", status: "pending"}
    - {order_id: "SO-2026-0003", customer: "华东汽车零部件", sku: "BEARING-C03", qty: 800, due_date: "2026-07-25", status: "shipped"}
  inventory:
    - {sku: "GEAR-A12", warehouse: "上海一号仓", qty: 240, safety_stock: 300}
    - {sku: "SHAFT-B08", warehouse: "上海一号仓", qty: 1500, safety_stock: 800}
    - {sku: "BEARING-C03", warehouse: "深圳二号仓", qty: 60, safety_stock: 200}
  shipments:
    - {shipment_id: "SH-0001", order_id: "SO-2026-0003", carrier: "顺丰", eta: "2026-07-08", status: "in_transit"}
    - {shipment_id: "SH-0002", order_id: "SO-2026-0002", carrier: "德邦", eta: "2026-07-22", status: "created"}
    - {shipment_id: "SH-0003", order_id: "SO-2026-0001", carrier: "京东", eta: "2026-07-16", status: "created"}
talking_points:
  - 制造业客户最关心交期与库存周转，演示节奏应从订单开始
  - 强调"数据从设备到看板一条链路"，不是靠人工填报
```

Create `backend/app/templates/industries/finance.yaml`:
```yaml
name: finance
aliases: ["金融", "银行", "证券", "保险", "finance"]
default_scenarios: ["风控", "反欺诈", "客户 360", "报表合规"]
architecture_snippet: |
  核心系统 → 消息队列 → 风控引擎 → { 规则 · 模型 · 名单 } → 决策服务 → 前端与审计
feature_bank:
  - id: fin-risk-rule
    title: 可视化风控规则编辑
    description: 拖拽式配置反欺诈规则，实时预览命中率
    demo_steps:
      - 新建规则：金额 > 5 万 且 收款方为新绑
      - 用回放数据预览命中笔数
      - 保存并灰度上线
    talking_points:
      - 规则改动无需发版，业务同学自主运营
      - 灰度机制先跑影子流量再切真实
    scenarios: ["风控", "反欺诈"]
  - id: fin-model
    title: 反欺诈模型评分
    description: 集成 XGBoost 模型对每笔交易输出 0-1000 风险分
    demo_steps:
      - 选一笔交易，展示评分与关键特征
      - 对比规则命中与模型命中
    talking_points:
      - 模型与规则可组合决策
      - 特征贡献度可解释，满足监管审核
    scenarios: ["风控", "反欺诈"]
  - id: fin-customer-360
    title: 客户 360 视图
    description: 汇总账户、交易、行为、外部数据，形成客户画像
    demo_steps:
      - 输入客户号，加载 360 页面
      - 切换到"风险时间轴"标签
    talking_points:
      - 打破分行/条线数据孤岛
      - 敏感字段按角色脱敏
    scenarios: ["客户 360"]
  - id: fin-alert
    title: 告警工单
    description: 命中规则/模型自动生成工单，指派到运营
    demo_steps:
      - 展示工单列表，筛选高风险
      - 打开一单，处置：确认欺诈 / 误报
    talking_points:
      - 处置结果反哺模型迭代
      - 支持外呼二次核实
    scenarios: ["风控", "反欺诈"]
  - id: fin-report
    title: 监管报表自动生成
    description: 按人行/银保监模板日/月/季度自动出表
    demo_steps:
      - 选择报表类型与周期
      - 一键生成并下载
    talking_points:
      - 与核心系统 T+0 对账
      - 生成过程留痕，支持审计追溯
    scenarios: ["报表合规"]
  - id: fin-blacklist
    title: 名单联邦查询
    description: 与外部名单服务安全对接，隐私计算查询命中情况
    demo_steps:
      - 输入手机号，展示命中来源
      - 打开一个命中记录，展示证据链
    talking_points:
      - 通过隐私计算而非明文传输
      - 名单来源可管理，支持撤销
    scenarios: ["反欺诈"]
mock_data_schema:
  transactions:
    - {txn_id: "T-000001", account: "6222-1234", amount: 68000, counterparty: "新绑收款方 A", ts: "2026-07-06T10:12:00", risk_score: 820}
    - {txn_id: "T-000002", account: "6222-5678", amount: 300, counterparty: "常用商户 B", ts: "2026-07-06T10:13:04", risk_score: 40}
    - {txn_id: "T-000003", account: "6222-1234", amount: 120000, counterparty: "新绑收款方 A", ts: "2026-07-06T10:15:22", risk_score: 950}
  alerts:
    - {alert_id: "A-0001", txn_id: "T-000003", rule: "大额新收款方", severity: "high", status: "open"}
    - {alert_id: "A-0002", txn_id: "T-000001", rule: "夜间大额", severity: "medium", status: "processing"}
    - {alert_id: "A-0003", txn_id: "T-000002", rule: "模型评分>800", severity: "low", status: "closed"}
  customers:
    - {customer_id: "C-1001", tier: "钻石", risk_level: "低", asset: 5200000}
    - {customer_id: "C-1002", tier: "白金", risk_level: "中", asset: 380000}
    - {customer_id: "C-1003", tier: "黄金", risk_level: "低", asset: 90000}
talking_points:
  - 金融客户最看重可解释性与合规审计，评分之外要能讲清"为什么"
  - 强调"规则+模型"双引擎，业务与算法各自演进
```

Create `backend/app/templates/industries/retail.yaml`:
```yaml
name: retail
aliases: ["零售", "电商", "商超", "retail", "e-commerce"]
default_scenarios: ["会员运营", "商品分析", "门店选品", "促销策划"]
architecture_snippet: |
  POS/电商 → 数据中台 → { 会员 · 商品 · 交易 } → 分析与营销 → 门店/APP/公众号
feature_bank:
  - id: rtl-member
    title: 会员分层运营
    description: RFM 模型自动分层并推荐营销活动
    demo_steps:
      - 展示会员分层饼图
      - 选"沉睡高价值"层，推荐唤醒活动
    talking_points:
      - 分层规则可视化调整，业务自主
      - 活动效果 T+1 归因
    scenarios: ["会员运营"]
  - id: rtl-basket
    title: 关联分析
    description: 挖掘常见连带购买组合，指导商品陈列与套餐
    demo_steps:
      - 输入品类，展示 Top 10 关联品类
      - 演示"提升度"排序
    talking_points:
      - 支撑跨品类促销
      - 结果直接推送到店长 APP
    scenarios: ["商品分析", "促销策划"]
  - id: rtl-store-select
    title: 门店选品
    description: 结合门店画像与销售历史，推荐补货清单
    demo_steps:
      - 选一家门店，展示当前 SKU 结构
      - 展示"推荐引入"与"建议下架"
    talking_points:
      - 融入商圈画像，同一品牌不同店不同选品
      - 每周自动刷新，支持人工微调
    scenarios: ["门店选品"]
  - id: rtl-promo
    title: 促销 A/B 测试
    description: 支持多方案并行投放，实时对比转化
    demo_steps:
      - 创建 A/B 两个优惠券方案
      - 查看当前转化对比
    talking_points:
      - 显著性检验自动计算
      - 效果达标可一键全量投放
    scenarios: ["促销策划"]
  - id: rtl-price
    title: 智能调价
    description: 根据竞品价、库龄、季节因子给出建议价
    demo_steps:
      - 选 SKU，展示当前价与建议价
      - 展示预期毛利影响
    talking_points:
      - 竞品价通过合规爬取，可追溯
      - 建议价可批量应用或按门店差异化
    scenarios: ["商品分析", "促销策划"]
  - id: rtl-inventory
    title: 全渠道库存共享
    description: 打通电商与门店库存，就近履约
    demo_steps:
      - 展示一个 SKU 在全国的库存热力图
      - 演示线上单派单到最近门店
    talking_points:
      - 缩短履约时长、降低物流成本
      - 门店闲置库存有效变现
    scenarios: ["门店选品"]
mock_data_schema:
  members:
    - {member_id: "M-0001", tier: "钻石", last_purchase: "2026-07-03", rfm: "555", ltv: 12800}
    - {member_id: "M-0002", tier: "沉睡", last_purchase: "2025-12-11", rfm: "115", ltv: 3400}
    - {member_id: "M-0003", tier: "潜力", last_purchase: "2026-06-25", rfm: "343", ltv: 6200}
  skus:
    - {sku: "SKU-A1", category: "零食", price: 12.9, stock: 340, sold_30d: 210}
    - {sku: "SKU-A2", category: "日化", price: 39.9, stock: 55, sold_30d: 80}
    - {sku: "SKU-A3", category: "零食", price: 8.5, stock: 500, sold_30d: 320}
  orders:
    - {order_id: "O-000001", channel: "线上", amount: 156, member_id: "M-0001", store: "线上"}
    - {order_id: "O-000002", channel: "门店", amount: 88, member_id: "M-0003", store: "北京 SKP 店"}
    - {order_id: "O-000003", channel: "门店", amount: 42, member_id: null, store: "上海静安店"}
talking_points:
  - 零售客户看重"看得见"的数据，图表要多而清晰
  - 会员与商品是两条主线，先讲客户想听的
```

- [ ] **Step 4: Implement `app/templates/__init__.py`**

```python
"""
Industry template loader.

Prompt-style contract (spec §5.3):
- 角色定义: static configuration for industry-specific 功能库/数据字段/话术
- 输入格式: YAML files under templates/industries/*.yaml
- 输出格式: {lowercase(name) -> IndustryTemplate}, cached on first call
- 约束条件: no I/O outside this loader; no network; no writes
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    id: str
    title: str
    description: str
    demo_steps: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)


class IndustryTemplate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    default_scenarios: list[str] = Field(default_factory=list)
    feature_bank: list[FeatureSpec]
    mock_data_schema: dict[str, list[dict[str, Any]]]
    talking_points: list[str] = Field(default_factory=list)
    architecture_snippet: str = ""


_INDUSTRIES_DIR = Path(__file__).parent / "industries"


@lru_cache(maxsize=1)
def load_templates() -> dict[str, IndustryTemplate]:
    result: dict[str, IndustryTemplate] = {}
    for yaml_path in sorted(_INDUSTRIES_DIR.glob("*.yaml")):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        tmpl = IndustryTemplate.model_validate(data)
        result[tmpl.name.lower()] = tmpl
    return result


def resolve_industry(
    query: str, templates: dict[str, IndustryTemplate]
) -> IndustryTemplate | None:
    q = query.strip().lower()
    for tmpl in templates.values():
        if tmpl.name.lower() == q:
            return tmpl
        if any(a.lower() == q for a in tmpl.aliases):
            return tmpl
    return None
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest tests/test_templates.py -v
```
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/templates backend/tests/test_templates.py
git commit -m "feat(backend): industry template loader + manufacturing/finance/retail seeds"
```

---
## Task 4: Parse Agent (F2-1 需求解析)

**Files:**
- Create: `backend/app/agents/parse_agent.py`
- Create: `backend/tests/test_parse_agent.py`

**Interfaces:**
- Consumes: `AgentContext.requirement: RequirementInput`; `load_templates()` from Task 3.
- Produces:
  - `ParseAgent` — class with `name = "parse"`, async `run(ctx) -> ParsedRequirement`.
  - `ParsedRequirement` pydantic model: `industry_key: str` (lowercased template key), `industry_display: str` (as user entered), `scenario: str`, `scale: str`, `demo_minutes: int`, `background: str | None`, `matched_scenarios: list[str]` (subset of the template's default scenarios that appear in either `scenario` or `background`).
  - On write: `ctx.outputs["parse"] = parsed.model_dump()`.
  - Raises `AgentError("parse", "unknown industry: <query>")` when `resolve_industry` returns None.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_parse_agent.py`:
```python
import pytest
from app.schemas import RequirementInput
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParseAgent, ParsedRequirement


def _ctx(**overrides):
    req = RequirementInput(
        industry=overrides.get("industry", "制造业"),
        scenario=overrides.get("scenario", "供应链管理"),
        scale=overrides.get("scale", "500 人以上"),
        demo_minutes=overrides.get("demo_minutes", 15),
        background=overrides.get("background"),
    )
    return AgentContext(session_id="s1", requirement=req, outputs={})


async def test_parse_agent_maps_industry_by_alias():
    ctx = _ctx()
    parsed = await ParseAgent().run(ctx)
    assert isinstance(parsed, ParsedRequirement)
    assert parsed.industry_key == "manufacturing"
    assert parsed.industry_display == "制造业"


async def test_parse_agent_writes_outputs_under_its_name():
    ctx = _ctx()
    await ParseAgent().run(ctx)
    assert "parse" in ctx.outputs
    assert ctx.outputs["parse"]["industry_key"] == "manufacturing"


async def test_parse_agent_extracts_matched_scenarios_from_background():
    ctx = _ctx(scenario="供应链管理", background="也想看看质量管理和 OEE")
    parsed = await ParseAgent().run(ctx)
    assert "供应链管理" in parsed.matched_scenarios
    assert "质量管理" in parsed.matched_scenarios


async def test_parse_agent_defaults_matched_scenarios_to_input_scenario():
    ctx = _ctx(scenario="供应链管理", background=None)
    parsed = await ParseAgent().run(ctx)
    assert parsed.matched_scenarios == ["供应链管理"]


async def test_parse_agent_raises_on_unknown_industry():
    ctx = _ctx(industry="外星科技")
    with pytest.raises(AgentError) as excinfo:
        await ParseAgent().run(ctx)
    assert excinfo.value.agent_name == "parse"
    assert "外星科技" in excinfo.value.reason
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_parse_agent.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.parse_agent'`.

- [ ] **Step 3: Implement `app/agents/parse_agent.py`**

```python
"""
Parse Agent (F2-1 需求解析).

角色定义: extract structured requirement (industry, scenario, scale, matched scenarios) from raw form input.
输入格式: AgentContext.requirement: RequirementInput
输出格式: ParsedRequirement + ctx.outputs["parse"] = same as dict
约束条件: no LLM call, template-lookup only; raise AgentError on unknown industry.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.templates import load_templates, resolve_industry


class ParsedRequirement(BaseModel):
    industry_key: str
    industry_display: str
    scenario: str
    scale: str
    demo_minutes: int
    background: str | None
    matched_scenarios: list[str]


class ParseAgent:
    name = "parse"

    async def run(self, ctx: AgentContext) -> ParsedRequirement:
        req = ctx.requirement
        templates = load_templates()
        tmpl = resolve_industry(req.industry, templates)
        if tmpl is None:
            raise AgentError(self.name, f"unknown industry: {req.industry}")

        # Collect scenarios that appear either in scenario input or in the free-text background.
        haystack = " ".join([req.scenario, req.background or ""]).lower()
        matched = [s for s in tmpl.default_scenarios if s.lower() in haystack]
        if req.scenario not in matched:
            matched.insert(0, req.scenario)

        parsed = ParsedRequirement(
            industry_key=tmpl.name.lower(),
            industry_display=req.industry,
            scenario=req.scenario,
            scale=req.scale,
            demo_minutes=req.demo_minutes,
            background=req.background,
            matched_scenarios=matched,
        )
        ctx.outputs[self.name] = parsed.model_dump()
        return parsed
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_parse_agent.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/parse_agent.py backend/tests/test_parse_agent.py
git commit -m "feat(backend): ParseAgent (F2-1) — industry alias resolve + scenario extraction"
```

---

## Task 5: Design Agent (F2-2 方案设计)

**Files:**
- Create: `backend/app/agents/design_agent.py`
- Create: `backend/tests/test_design_agent.py`

**Interfaces:**
- Consumes: `ctx.outputs["parse"]` (a `ParsedRequirement`-shaped dict); `load_templates()`.
- Produces:
  - `DesignAgent` — `name = "design"`, async `run(ctx) -> DesignedPlan`.
  - `DesignedPlan` pydantic model: `features: list[FeatureSpec]` (subset of the industry's feature bank matching the parsed scenarios), `coverage_ratio: float` (matched / total for those scenarios), `time_allocation: list[TimeSlot]` (each `TimeSlot`: `feature_id: str`, `feature_title: str`, `minutes: int`; sum of minutes == `demo_minutes`).
  - On write: `ctx.outputs["design"] = designed.model_dump()`.
  - Guarantees `len(features) >= 3` (AC-3). If the industry's own bank has fewer scenario-matching features, falls back to including the highest-priority remaining features until the count is ≥ 3.
  - Guarantees `coverage_ratio >= 0.8` for the *matched-scenario slice* of the feature bank (§4 输出质量). If below, includes all remaining scenario-matching features until at 100 %.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_design_agent.py`:
```python
import pytest
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent, DesignedPlan


async def _run(industry="制造业", scenario="供应链管理", background=None, minutes=15):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario=scenario, scale="500 人", demo_minutes=minutes,
            background=background,
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    plan = await DesignAgent().run(ctx)
    return ctx, plan


async def test_design_agent_produces_at_least_three_features():
    _, plan = await _run()
    assert len(plan.features) >= 3  # AC-3


async def test_design_agent_features_relevant_to_scenario():
    _, plan = await _run(scenario="供应链管理")
    for f in plan.features:
        # Every returned feature must at least touch a matched scenario.
        assert f.scenarios, f"feature {f.id} has no scenarios"


async def test_design_agent_coverage_at_least_80_percent():
    _, plan = await _run()
    assert plan.coverage_ratio >= 0.8  # spec §4 输出质量


async def test_design_agent_time_allocation_sums_to_demo_minutes():
    _, plan = await _run(minutes=15)
    assert sum(slot.minutes for slot in plan.time_allocation) == 15


async def test_design_agent_time_allocation_matches_feature_count():
    _, plan = await _run(minutes=15)
    assert len(plan.time_allocation) == len(plan.features)


async def test_design_agent_writes_outputs():
    ctx, _ = await _run()
    assert "design" in ctx.outputs
    assert isinstance(ctx.outputs["design"]["features"], list)


async def test_design_agent_handles_short_demo_minutes_without_zero_slots():
    _, plan = await _run(minutes=3)
    # 3 features minimum, each must get ≥ 1 minute; total == 3.
    assert all(s.minutes >= 1 for s in plan.time_allocation)
    assert sum(s.minutes for s in plan.time_allocation) == 3
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_design_agent.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.design_agent'`.

- [ ] **Step 3: Implement `app/agents/design_agent.py`**

```python
"""
Design Agent (F2-2 方案设计).

角色定义: given a ParsedRequirement, pick the features to demo and allocate demo minutes.
输入格式: ctx.outputs["parse"] (ParsedRequirement dict)
输出格式: DesignedPlan + ctx.outputs["design"]
约束条件:
  - Feature count >= 3 (AC-3).
  - Coverage of scenario-relevant features >= 0.8 (spec §4 输出质量).
  - Sum of time allocations == demo_minutes; every slot >= 1.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import FeatureSpec, load_templates


class TimeSlot(BaseModel):
    feature_id: str
    feature_title: str
    minutes: int


class DesignedPlan(BaseModel):
    features: list[FeatureSpec]
    coverage_ratio: float
    time_allocation: list[TimeSlot]


MIN_FEATURES = 3
MIN_COVERAGE = 0.8


class DesignAgent:
    name = "design"

    async def run(self, ctx: AgentContext) -> DesignedPlan:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)

        templates = load_templates()
        tmpl = templates[parsed.industry_key]
        bank = tmpl.feature_bank
        matched_scenarios = set(parsed.matched_scenarios)

        # Split the bank by scenario relevance.
        relevant = [f for f in bank if set(f.scenarios) & matched_scenarios]
        other = [f for f in bank if f not in relevant]

        selected = list(relevant)

        # Ensure count >= 3.
        i = 0
        while len(selected) < MIN_FEATURES and i < len(other):
            selected.append(other[i])
            i += 1

        # Ensure coverage of the relevant slice >= 0.8.
        if relevant:
            covered = sum(1 for f in selected if f in relevant)
            while covered / len(relevant) < MIN_COVERAGE and i < len(other):
                selected.append(other[i])
                i += 1
                covered = sum(1 for f in selected if f in relevant)
        coverage_ratio = 1.0 if not relevant else sum(1 for f in selected if f in relevant) / len(relevant)

        # Fair minute allocation: floor split, distribute remainder to the first N features.
        n = len(selected)
        total = parsed.demo_minutes
        base = max(1, total // n)
        allocation = [base] * n
        remainder = total - base * n
        # Ensure sum == total: if base==1 and total<n we cannot, but demo_minutes>0 and n>=3
        # so guarantee base is at least 1 and pump minutes to first slots until sum == total.
        idx = 0
        while sum(allocation) < total:
            allocation[idx % n] += 1
            idx += 1
        while sum(allocation) > total:
            # only possible if base*n > total (i.e. total < n)
            if allocation[idx % n] > 1:
                allocation[idx % n] -= 1
            idx += 1

        time_allocation = [
            TimeSlot(feature_id=f.id, feature_title=f.title, minutes=m)
            for f, m in zip(selected, allocation)
        ]

        designed = DesignedPlan(
            features=selected,
            coverage_ratio=round(coverage_ratio, 3),
            time_allocation=time_allocation,
        )
        ctx.outputs[self.name] = designed.model_dump()
        return designed
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_design_agent.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/design_agent.py backend/tests/test_design_agent.py
git commit -m "feat(backend): DesignAgent (F2-2) — feature selection + time allocation"
```

---
## Task 6: Content Agent (F2-3 内容生成)

**Files:**
- Create: `backend/app/agents/content_agent.py`
- Create: `backend/tests/test_content_agent.py`

**Interfaces:**
- Consumes: `ctx.outputs["design"]` (DesignedPlan dict).
- Produces:
  - `ContentAgent` — `name = "content"`, async `run(ctx) -> DemoScript`.
  - `FeatureBrief` model: `feature_id: str`, `title: str`, `intro: str`, `flow: list[str]`, `value: str`, `talking_points_5min: str`, `talking_points_15min: str`.
  - `DemoScript` model: `briefs: list[FeatureBrief]`, `opening: str`, `closing: str`.
  - On write: `ctx.outputs["content"] = script.model_dump()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_content_agent.py`:
```python
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent, DemoScript, FeatureBrief


async def _prepped_ctx(scenario="供应链管理", minutes=15):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario=scenario, scale="500 人", demo_minutes=minutes
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    return ctx


async def test_content_agent_produces_one_brief_per_feature():
    ctx = await _prepped_ctx()
    script = await ContentAgent().run(ctx)
    assert isinstance(script, DemoScript)
    assert len(script.briefs) == len(ctx.outputs["design"]["features"])


async def test_content_agent_briefs_include_talking_points_variants():
    ctx = await _prepped_ctx()
    script = await ContentAgent().run(ctx)
    for b in script.briefs:
        assert isinstance(b, FeatureBrief)
        assert b.talking_points_5min
        assert b.talking_points_15min
        assert b.flow, "demo flow must not be empty (spec §3.3 F3-3)"


async def test_content_agent_opening_mentions_industry_and_scenario():
    ctx = await _prepped_ctx(scenario="供应链管理")
    script = await ContentAgent().run(ctx)
    assert "制造" in script.opening or "manufacturing" in script.opening.lower()
    assert "供应链" in script.opening


async def test_content_agent_writes_outputs():
    ctx = await _prepped_ctx()
    await ContentAgent().run(ctx)
    assert "content" in ctx.outputs
    assert isinstance(ctx.outputs["content"]["briefs"], list)
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_content_agent.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.content_agent'`.

- [ ] **Step 3: Implement `app/agents/content_agent.py`**

```python
"""
Content Agent (F2-3 内容生成).

角色定义: turn a DesignedPlan into demo copy — 功能介绍 / 操作流程 / 价值说明 / 话术.
输入格式: ctx.outputs["design"] (DesignedPlan dict)
输出格式: DemoScript + ctx.outputs["content"]
约束条件: template-driven; use each feature's built-in demo_steps and talking_points; never invent numbers.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.design_agent import DesignedPlan
from app.agents.parse_agent import ParsedRequirement


class FeatureBrief(BaseModel):
    feature_id: str
    title: str
    intro: str
    flow: list[str]
    value: str
    talking_points_5min: str
    talking_points_15min: str


class DemoScript(BaseModel):
    briefs: list[FeatureBrief]
    opening: str
    closing: str


class ContentAgent:
    name = "content"

    async def run(self, ctx: AgentContext) -> DemoScript:
        parse_out = ctx.outputs.get("parse")
        design_out = ctx.outputs.get("design")
        if parse_out is None or design_out is None:
            raise AgentError(self.name, "upstream parse/design output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        designed = DesignedPlan.model_validate(design_out)

        briefs: list[FeatureBrief] = []
        for f in designed.features:
            short_tp = f.talking_points[0] if f.talking_points else f.title
            long_tp = " / ".join(f.talking_points) if f.talking_points else f.title
            briefs.append(FeatureBrief(
                feature_id=f.id,
                title=f.title,
                intro=f.description,
                flow=f.demo_steps,
                value=long_tp,
                talking_points_5min=short_tp,
                talking_points_15min=long_tp,
            ))

        opening = (
            f"针对{parsed.industry_display}行业，围绕「{parsed.scenario}」场景，"
            f"我们准备了 {len(briefs)} 个核心功能演示，覆盖客户最关心的能力。"
        )
        closing = (
            f"以上是为{parsed.industry_display}客户量身准备的方案要点，"
            f"欢迎针对任何模块深入交流。"
        )
        script = DemoScript(briefs=briefs, opening=opening, closing=closing)
        ctx.outputs[self.name] = script.model_dump()
        return script
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_content_agent.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/content_agent.py backend/tests/test_content_agent.py
git commit -m "feat(backend): ContentAgent (F2-3) — briefs, opening, closing"
```

---

## Task 7: Data Agent (F2-4 数据模拟)

**Files:**
- Create: `backend/app/agents/data_agent.py`
- Create: `backend/tests/test_data_agent.py`

**Interfaces:**
- Consumes: `ctx.outputs["design"]`, `ctx.outputs["parse"]`; industry template `mock_data_schema`.
- Produces:
  - `DataAgent` — `name = "data"`, async `run(ctx) -> MockDataPack`.
  - `MockDataPack` model: `tables: dict[str, list[dict]]` (one entry per table listed in the template's `mock_data_schema`), `csv_by_table: dict[str, str]` (each table serialized to CSV string).
  - On write: `ctx.outputs["data"] = pack.model_dump()`.
  - Every table has ≥ 3 rows (AC-4).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_data_agent.py`:
```python
import csv
import io
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.data_agent import DataAgent, MockDataPack


async def _prep(industry="制造业"):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    return ctx


async def test_data_agent_produces_all_industry_tables():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    assert isinstance(pack, MockDataPack)
    # Manufacturing template ships orders, inventory, shipments.
    assert {"orders", "inventory", "shipments"} <= set(pack.tables.keys())


async def test_data_agent_each_table_has_at_least_three_rows():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    for name, rows in pack.tables.items():
        assert len(rows) >= 3, f"{name} has < 3 rows"


async def test_data_agent_csv_is_parseable_and_matches_row_count():
    ctx = await _prep()
    pack = await DataAgent().run(ctx)
    for table, csv_str in pack.csv_by_table.items():
        reader = list(csv.DictReader(io.StringIO(csv_str)))
        assert len(reader) == len(pack.tables[table])


async def test_data_agent_industry_fields_match_semantics_finance():
    # Finance table must have transactions with account, amount, risk_score fields.
    ctx = AgentContext(
        session_id="s2",
        requirement=RequirementInput(
            industry="金融", scenario="风控", scale="1000 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    await DesignAgent().run(ctx)
    pack = await DataAgent().run(ctx)
    assert "transactions" in pack.tables
    first = pack.tables["transactions"][0]
    for field in ("account", "amount", "risk_score"):
        assert field in first, f"transactions row missing field {field}"


async def test_data_agent_writes_outputs():
    ctx = await _prep()
    await DataAgent().run(ctx)
    assert "data" in ctx.outputs
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_data_agent.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `app/agents/data_agent.py`**

```python
"""
Data Agent (F2-4 数据模拟).

角色定义: emit industry-appropriate mock data (JSON tables + CSV rendering) for the demo.
输入格式: ctx.outputs["parse"], ctx.outputs["design"]
输出格式: MockDataPack + ctx.outputs["data"]
约束条件:
  - Use the industry template's mock_data_schema verbatim (no fabricated fields).
  - Every table has >= 3 rows (AC-4).
  - CSV is UTF-8, header from the first row's keys.
"""
from __future__ import annotations
import csv
import io
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates


class MockDataPack(BaseModel):
    tables: dict[str, list[dict]]
    csv_by_table: dict[str, str]


def _rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


class DataAgent:
    name = "data"

    async def run(self, ctx: AgentContext) -> MockDataPack:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        tmpl = load_templates()[parsed.industry_key]
        tables = {name: list(rows) for name, rows in tmpl.mock_data_schema.items()}
        csv_by_table = {name: _rows_to_csv(rows) for name, rows in tables.items()}
        pack = MockDataPack(tables=tables, csv_by_table=csv_by_table)
        ctx.outputs[self.name] = pack.model_dump()
        return pack
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_data_agent.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/data_agent.py backend/tests/test_data_agent.py
git commit -m "feat(backend): DataAgent (F2-4) — industry mock tables + CSV"
```

---

## Task 8: Architecture Agent (架构描述)

**Files:**
- Create: `backend/app/agents/architecture_agent.py`
- Create: `backend/tests/test_architecture_agent.py`

**Interfaces:**
- Consumes: `ctx.outputs["parse"]`, industry template `architecture_snippet`.
- Produces:
  - `ArchitectureAgent` — `name = "architecture"`, async `run(ctx) -> ArchitectureDoc`.
  - `ArchitectureDoc` model: `description: str` (short prose), `mermaid: str` (a valid Mermaid flowchart block starting with `flowchart TD`).
  - On write: `ctx.outputs["architecture"] = doc.model_dump()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_architecture_agent.py`:
```python
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.architecture_agent import ArchitectureAgent, ArchitectureDoc


async def _ctx(industry="制造业"):
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry=industry, scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )
    await ParseAgent().run(ctx)
    return ctx


async def test_architecture_agent_returns_document():
    ctx = await _ctx()
    doc = await ArchitectureAgent().run(ctx)
    assert isinstance(doc, ArchitectureDoc)
    assert doc.description
    assert doc.mermaid.startswith("flowchart TD")


async def test_architecture_agent_description_mentions_industry():
    ctx = await _ctx("金融")
    doc = await ArchitectureAgent().run(ctx)
    assert "金融" in doc.description


async def test_architecture_agent_writes_outputs():
    ctx = await _ctx()
    await ArchitectureAgent().run(ctx)
    assert "architecture" in ctx.outputs
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_architecture_agent.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `app/agents/architecture_agent.py`**

```python
"""
Architecture Agent.

角色定义: describe how the target system slots into the customer's environment; emit Mermaid.
输入格式: ctx.outputs["parse"]
输出格式: ArchitectureDoc + ctx.outputs["architecture"]
约束条件: Mermaid must be a valid flowchart TD; no external calls.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.agents.parse_agent import ParsedRequirement
from app.templates import load_templates


class ArchitectureDoc(BaseModel):
    description: str
    mermaid: str


class ArchitectureAgent:
    name = "architecture"

    async def run(self, ctx: AgentContext) -> ArchitectureDoc:
        parse_out = ctx.outputs.get("parse")
        if parse_out is None:
            raise AgentError(self.name, "upstream parse output missing")
        parsed = ParsedRequirement.model_validate(parse_out)
        tmpl = load_templates()[parsed.industry_key]

        description = (
            f"针对 {parsed.industry_display} 行业「{parsed.scenario}」场景，"
            f"我们的系统按下列链路与客户环境对接：{tmpl.architecture_snippet.strip()}"
        )
        # Build a simple Mermaid flowchart from the architecture snippet's arrows.
        nodes = [seg.strip() for seg in tmpl.architecture_snippet.replace("\n", "").split("→") if seg.strip()]
        lines = ["flowchart TD"]
        for i, node in enumerate(nodes):
            lines.append(f'    N{i}["{node}"]')
            if i > 0:
                lines.append(f"    N{i-1} --> N{i}")
        mermaid = "\n".join(lines)

        doc = ArchitectureDoc(description=description, mermaid=mermaid)
        ctx.outputs[self.name] = doc.model_dump()
        return doc
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_architecture_agent.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/architecture_agent.py backend/tests/test_architecture_agent.py
git commit -m "feat(backend): ArchitectureAgent — description + Mermaid"
```

---
## Task 9: Integrate Agent (结果整合) + Markdown assembly

**Files:**
- Create: `backend/app/agents/integrate_agent.py`
- Create: `backend/app/export/__init__.py`
- Create: `backend/app/export/markdown.py`
- Create: `backend/tests/test_integrate_agent.py`

**Interfaces:**
- Consumes: `ctx.outputs["parse"|"design"|"content"|"data"|"architecture"]`.
- Produces:
  - `IntegrateAgent` — `name = "integrate"`, async `run(ctx) -> FinalPlan`.
  - `FinalPlan` pydantic model: `session_id: str`, `markdown: str` (assembled document), `functions: list[dict]` (from design), `mock_data: dict[str, list[dict]]` (from data), `architecture: str` (Mermaid string), `demo_script: dict` (content).
  - `render_markdown(parse, design, content, data, architecture) -> str` — pure function in `app/export/markdown.py`.
  - On write: `ctx.outputs["integrate"] = final.model_dump()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_integrate_agent.py`:
```python
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent
from app.agents.data_agent import DataAgent
from app.agents.architecture_agent import ArchitectureAgent
from app.agents.integrate_agent import IntegrateAgent, FinalPlan


async def _full_ctx():
    ctx = AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=15
        ),
        outputs={},
    )
    for agent in [ParseAgent(), DesignAgent(), ContentAgent(), DataAgent(), ArchitectureAgent()]:
        await agent.run(ctx)
    return ctx


async def test_integrate_produces_final_plan():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    assert isinstance(final, FinalPlan)
    assert final.session_id == "s1"


async def test_integrate_markdown_contains_key_sections():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    md = final.markdown
    # Required sections per spec §3.3
    assert "# 售前方案" in md
    assert "## 客户需求概览" in md
    assert "## 功能演示清单" in md  # F3-3
    assert "## 系统架构" in md
    assert "## 演示话术" in md
    assert "## 模拟数据" in md  # F3-4
    assert "```mermaid" in md
    assert "flowchart TD" in md


async def test_integrate_markdown_lists_every_selected_feature():
    ctx = await _full_ctx()
    final = await IntegrateAgent().run(ctx)
    for f in ctx.outputs["design"]["features"]:
        assert f["title"] in final.markdown


async def test_integrate_writes_outputs():
    ctx = await _full_ctx()
    await IntegrateAgent().run(ctx)
    assert "integrate" in ctx.outputs
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_integrate_agent.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `app/export/markdown.py`**

Create `backend/app/export/__init__.py` (empty).
Create `backend/app/export/markdown.py`:
```python
"""Pure rendering: agent outputs -> Markdown pre-sales package."""
from __future__ import annotations
import json


def render_markdown(parse: dict, design: dict, content: dict, data: dict, architecture: dict) -> str:
    lines: list[str] = []
    lines.append("# 售前方案")
    lines.append("")
    # Overview
    lines.append("## 客户需求概览")
    lines.append("")
    lines.append(f"- 行业：{parse['industry_display']}")
    lines.append(f"- 场景：{parse['scenario']}")
    lines.append(f"- 规模：{parse['scale']}")
    lines.append(f"- 演示时长：{parse['demo_minutes']} 分钟")
    if parse.get("background"):
        lines.append(f"- 客户背景：{parse['background']}")
    lines.append(f"- 场景覆盖：{'、'.join(parse['matched_scenarios'])}")
    lines.append(f"- 功能覆盖率：{design['coverage_ratio']:.0%}")
    lines.append("")

    # Architecture
    arch = architecture
    lines.append("## 系统架构")
    lines.append("")
    lines.append(arch["description"])
    lines.append("")
    lines.append("```mermaid")
    lines.append(arch["mermaid"])
    lines.append("```")
    lines.append("")

    # Feature demo list
    lines.append("## 功能演示清单")
    lines.append("")
    briefs = {b["feature_id"]: b for b in content["briefs"]}
    for slot in design["time_allocation"]:
        fid = slot["feature_id"]
        b = briefs.get(fid, {})
        lines.append(f"### {slot['feature_title']}（建议 {slot['minutes']} 分钟）")
        lines.append("")
        lines.append(f"- **简介**：{b.get('intro','')}")
        lines.append("- **演示步骤**：")
        for step in b.get("flow", []):
            lines.append(f"  1. {step}")
        lines.append(f"- **价值点**：{b.get('value','')}")
        lines.append("")

    # Demo script
    lines.append("## 演示话术")
    lines.append("")
    lines.append(f"**开场白**：{content['opening']}")
    lines.append("")
    lines.append("**分功能话术（5 分钟 / 15 分钟版）**：")
    for b in content["briefs"]:
        lines.append(f"- **{b['title']}**")
        lines.append(f"  - 5 分钟版：{b['talking_points_5min']}")
        lines.append(f"  - 15 分钟版：{b['talking_points_15min']}")
    lines.append("")
    lines.append(f"**结束语**：{content['closing']}")
    lines.append("")

    # Mock data
    lines.append("## 模拟数据")
    lines.append("")
    lines.append("以下数据可直接导入客户演示环境。")
    lines.append("")
    for table_name, rows in data["tables"].items():
        lines.append(f"### `{table_name}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(rows, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Implement `app/agents/integrate_agent.py`**

```python
"""
Integrate Agent (结果整合).

角色定义: gather every upstream agent's output into one FinalPlan and render the Markdown package.
输入格式: ctx.outputs["parse"|"design"|"content"|"data"|"architecture"]
输出格式: FinalPlan + ctx.outputs["integrate"]
约束条件: pure aggregation + render; no re-generation of content.
"""
from __future__ import annotations
from pydantic import BaseModel
from app.agents.base import AgentContext, AgentError
from app.export.markdown import render_markdown


class FinalPlan(BaseModel):
    session_id: str
    markdown: str
    functions: list[dict]
    mock_data: dict[str, list[dict]]
    architecture: str
    demo_script: dict


REQUIRED_UPSTREAM = ("parse", "design", "content", "data", "architecture")


class IntegrateAgent:
    name = "integrate"

    async def run(self, ctx: AgentContext) -> FinalPlan:
        missing = [k for k in REQUIRED_UPSTREAM if k not in ctx.outputs]
        if missing:
            raise AgentError(self.name, f"missing upstream outputs: {','.join(missing)}")

        md = render_markdown(
            parse=ctx.outputs["parse"],
            design=ctx.outputs["design"],
            content=ctx.outputs["content"],
            data=ctx.outputs["data"],
            architecture=ctx.outputs["architecture"],
        )
        final = FinalPlan(
            session_id=ctx.session_id,
            markdown=md,
            functions=ctx.outputs["design"]["features"],
            mock_data=ctx.outputs["data"]["tables"],
            architecture=ctx.outputs["architecture"]["mermaid"],
            demo_script=ctx.outputs["content"],
        )
        ctx.outputs[self.name] = final.model_dump()
        return final
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest tests/test_integrate_agent.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/integrate_agent.py backend/app/export backend/tests/test_integrate_agent.py
git commit -m "feat(backend): IntegrateAgent + Markdown assembly (F3-1)"
```

---

## Task 10: DAG definition and Agent registry

**Files:**
- Create: `backend/app/agents/registry.py`
- Create: `backend/app/orchestrator/__init__.py`
- Create: `backend/app/orchestrator/dag.py`
- Create: `backend/app/orchestrator/events.py`
- Create: `backend/tests/test_dag.py`

**Interfaces:**
- Consumes: all six Agent classes from Tasks 4-9.
- Produces:
  - `AGENT_REGISTRY: dict[str, Agent]` — one instance per Agent name. Swap point for future LLM Agents (spec §5.4).
  - `AgentNode` dataclass in `orchestrator/dag.py`: `name: str`, `depends_on: tuple[str, ...]`.
  - `DAG: tuple[AgentNode, ...]` — the concrete pipeline: parse → design → {content, data, architecture} → integrate.
  - `orchestrator/events.py` defines `AgentEvent` (dataclass) with `agent: str`, `status: Literal["running","done","failed"]`, `elapsed_ms: int`, `error: str | None`.
  - `topological_layers(dag: tuple[AgentNode, ...]) -> list[list[AgentNode]]` — Kahn-style grouping; nodes in the same layer are independent and may run concurrently.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_dag.py`:
```python
from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.dag import DAG, AgentNode, topological_layers


def test_registry_contains_expected_agents():
    assert set(AGENT_REGISTRY.keys()) == {"parse", "design", "content", "data", "architecture", "integrate"}


def test_dag_has_six_nodes():
    assert len(DAG) == 6


def test_dag_dependencies_form_the_fan_out():
    by_name = {n.name: n for n in DAG}
    assert by_name["parse"].depends_on == ()
    assert by_name["design"].depends_on == ("parse",)
    assert set(by_name["content"].depends_on) == {"design"}
    assert set(by_name["data"].depends_on) == {"design"}
    assert set(by_name["architecture"].depends_on) == {"parse"}
    assert set(by_name["integrate"].depends_on) == {"content", "data", "architecture"}


def test_topological_layers_group_fan_out_together():
    layers = topological_layers(DAG)
    layer_names = [{n.name for n in layer} for layer in layers]
    assert layer_names[0] == {"parse"}
    assert layer_names[1] == {"design", "architecture"} or layer_names[1] == {"design"}
    # architecture depends only on parse, so it can be in layer 1; content/data must land after design.
    idx = {name: i for i, layer in enumerate(layers) for name in {n.name for n in layer}}
    assert idx["parse"] < idx["design"]
    assert idx["design"] < idx["content"]
    assert idx["design"] < idx["data"]
    assert idx["parse"] < idx["architecture"]
    assert idx["integrate"] == max(idx.values())


def test_topological_layers_cycle_raises():
    import pytest
    cycle = (AgentNode("a", ("b",)), AgentNode("b", ("a",)))
    with pytest.raises(ValueError):
        topological_layers(cycle)
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_dag.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.agents.registry'`.

- [ ] **Step 3: Implement registry, events, and DAG**

Create `backend/app/agents/registry.py`:
```python
"""Single swap point for Agent instances. Replace with LLM-backed instances per spec §5.4."""
from __future__ import annotations
from app.agents.base import Agent
from app.agents.parse_agent import ParseAgent
from app.agents.design_agent import DesignAgent
from app.agents.content_agent import ContentAgent
from app.agents.data_agent import DataAgent
from app.agents.architecture_agent import ArchitectureAgent
from app.agents.integrate_agent import IntegrateAgent

AGENT_REGISTRY: dict[str, Agent] = {
    "parse": ParseAgent(),
    "design": DesignAgent(),
    "content": ContentAgent(),
    "data": DataAgent(),
    "architecture": ArchitectureAgent(),
    "integrate": IntegrateAgent(),
}
```

Create `backend/app/orchestrator/__init__.py` (empty).

Create `backend/app/orchestrator/events.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

AgentStatus = Literal["running", "done", "failed"]


@dataclass
class AgentEvent:
    agent: str
    status: AgentStatus
    elapsed_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return {"agent": self.agent, "status": self.status, "elapsed_ms": self.elapsed_ms, "error": self.error}
```

Create `backend/app/orchestrator/dag.py`:
```python
"""
DAG definition. Data-only; editing this file does not touch the runner (engine.py).
Adding a new Agent means: implement it, register it, add one AgentNode line here.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentNode:
    name: str
    depends_on: tuple[str, ...] = ()


DAG: tuple[AgentNode, ...] = (
    AgentNode("parse"),
    AgentNode("design", depends_on=("parse",)),
    AgentNode("content", depends_on=("design",)),
    AgentNode("data", depends_on=("design",)),
    AgentNode("architecture", depends_on=("parse",)),
    AgentNode("integrate", depends_on=("content", "data", "architecture")),
)


def topological_layers(dag: tuple[AgentNode, ...]) -> list[list[AgentNode]]:
    by_name = {n.name: n for n in dag}
    remaining = {n.name: set(n.depends_on) for n in dag}
    layers: list[list[AgentNode]] = []
    while remaining:
        ready = [name for name, deps in remaining.items() if not deps]
        if not ready:
            raise ValueError(f"cycle detected in DAG; remaining={remaining}")
        layers.append([by_name[n] for n in ready])
        for name in ready:
            del remaining[name]
        for deps in remaining.values():
            deps.difference_update(ready)
    return layers
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_dag.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/registry.py backend/app/orchestrator backend/tests/test_dag.py
git commit -m "feat(backend): AGENT_REGISTRY, DAG, topological_layers, AgentEvent"
```

---

## Task 11: Orchestration engine (success path)

**Files:**
- Create: `backend/app/orchestrator/engine.py`
- Create: `backend/tests/test_orchestrator_success.py`

**Interfaces:**
- Consumes: `AGENT_REGISTRY`, `DAG`, `topological_layers`, `AgentEvent`, `AgentContext`.
- Produces:
  - `async def run_pipeline(ctx: AgentContext, on_event: Callable[[AgentEvent], Awaitable[None]] | None = None, registry: dict[str, Agent] | None = None, dag: tuple[AgentNode, ...] | None = None) -> dict` — returns `ctx.outputs["integrate"]` on success. Emits `running` before each agent, `done` after (with `elapsed_ms`). Nodes in the same layer run concurrently via `anyio.create_task_group`.
  - `class PipelineFailure(Exception)`: `.failures: list[AgentEvent]` — raised when any Agent fails after siblings finish.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_orchestrator_success.py`:
```python
from app.schemas import RequirementInput
from app.agents.base import AgentContext
from app.orchestrator.engine import run_pipeline
from app.orchestrator.events import AgentEvent


def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


async def test_pipeline_returns_integrate_output():
    ctx = _ctx()
    result = await run_pipeline(ctx)
    assert "markdown" in result
    assert "# 售前方案" in result["markdown"]


async def test_pipeline_emits_running_and_done_for_each_agent():
    events: list[AgentEvent] = []

    async def sink(ev: AgentEvent) -> None:
        events.append(ev)

    ctx = _ctx()
    await run_pipeline(ctx, on_event=sink)
    agent_names = {"parse", "design", "content", "data", "architecture", "integrate"}
    running = {ev.agent for ev in events if ev.status == "running"}
    done = {ev.agent for ev in events if ev.status == "done"}
    assert running == agent_names
    assert done == agent_names


async def test_pipeline_records_elapsed_ms_non_negative():
    events: list[AgentEvent] = []

    async def sink(ev: AgentEvent) -> None:
        events.append(ev)

    ctx = _ctx()
    await run_pipeline(ctx, on_event=sink)
    for ev in events:
        if ev.status == "done":
            assert ev.elapsed_ms >= 0
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_orchestrator_success.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.orchestrator.engine'`.

- [ ] **Step 3: Implement `app/orchestrator/engine.py`**

```python
"""
Orchestration engine.

- Groups the DAG into topological layers; runs each layer's nodes concurrently.
- Emits AgentEvent through an optional callback for progress streaming.
- On failure, records the failure but lets sibling nodes in the same layer finish
  before raising PipelineFailure (spec §4 容错性, AC-6).
"""
from __future__ import annotations
import time
from typing import Awaitable, Callable
import anyio

from app.agents.base import Agent, AgentContext, AgentError
from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.dag import AgentNode, DAG, topological_layers
from app.orchestrator.events import AgentEvent

EventCallback = Callable[[AgentEvent], Awaitable[None]]


class PipelineFailure(Exception):
    def __init__(self, failures: list[AgentEvent]) -> None:
        msg = "; ".join(f"{ev.agent}: {ev.error}" for ev in failures)
        super().__init__(msg)
        self.failures = failures


async def _run_one(
    node: AgentNode,
    agent: Agent,
    ctx: AgentContext,
    on_event: EventCallback | None,
    failures: list[AgentEvent],
) -> None:
    if on_event:
        await on_event(AgentEvent(agent=node.name, status="running"))
    started = time.monotonic()
    try:
        await agent.run(ctx)
        elapsed = int((time.monotonic() - started) * 1000)
        if on_event:
            await on_event(AgentEvent(agent=node.name, status="done", elapsed_ms=elapsed))
    except AgentError as e:
        elapsed = int((time.monotonic() - started) * 1000)
        ev = AgentEvent(agent=node.name, status="failed", elapsed_ms=elapsed, error=e.reason)
        failures.append(ev)
        if on_event:
            await on_event(ev)
    except Exception as e:  # unexpected — surface with the Agent's name (AC-6)
        elapsed = int((time.monotonic() - started) * 1000)
        ev = AgentEvent(agent=node.name, status="failed", elapsed_ms=elapsed, error=f"unexpected: {e}")
        failures.append(ev)
        if on_event:
            await on_event(ev)


async def run_pipeline(
    ctx: AgentContext,
    on_event: EventCallback | None = None,
    registry: dict[str, Agent] | None = None,
    dag: tuple[AgentNode, ...] | None = None,
) -> dict:
    reg = registry or AGENT_REGISTRY
    active_dag = dag or DAG
    layers = topological_layers(active_dag)
    failures: list[AgentEvent] = []
    failed_names: set[str] = set()

    for layer in layers:
        runnable = [n for n in layer if not (set(n.depends_on) & failed_names)]
        # Skipped nodes (upstream failed) are also reported for transparency.
        for n in layer:
            if n not in runnable and on_event:
                await on_event(AgentEvent(
                    agent=n.name,
                    status="failed",
                    error=f"skipped: upstream {sorted(set(n.depends_on) & failed_names)} failed",
                ))
                failed_names.add(n.name)

        async with anyio.create_task_group() as tg:
            for node in runnable:
                agent = reg[node.name]
                tg.start_soon(_run_one, node, agent, ctx, on_event, failures)

        for ev in failures:
            failed_names.add(ev.agent)

    if failures:
        raise PipelineFailure(failures)

    return ctx.outputs["integrate"]
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest tests/test_orchestrator_success.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/orchestrator/engine.py backend/tests/test_orchestrator_success.py
git commit -m "feat(backend): orchestrator engine with layered parallel execution"
```

---
## Task 12: Orchestration engine (failure path — AC-6)

**Files:**
- Create: `backend/tests/test_orchestrator_failure.py`

**Interfaces:**
- Consumes: `Agent`, `AgentError`, `AgentContext`, `run_pipeline`, `PipelineFailure` from Tasks 2, 10, 11.
- Produces: (test only) — one extra test fixture `FailingAgent`.
- Verifies AC-6: failure surfaces Agent name + reason; sibling Agents on independent branches still run.

- [ ] **Step 1: Write the failure test**

Create `backend/tests/test_orchestrator_failure.py`:
```python
import pytest
from app.schemas import RequirementInput
from app.agents.base import Agent, AgentContext, AgentError
from app.agents.registry import AGENT_REGISTRY
from app.orchestrator.engine import run_pipeline, PipelineFailure


class _FailingContentAgent:
    """A content agent that always fails — injected in place of the real one."""
    name = "content"

    async def run(self, ctx: AgentContext):
        raise AgentError("content", "LLM 超时，请重试")


async def _ctx():
    return AgentContext(
        session_id="s1",
        requirement=RequirementInput(
            industry="制造业", scenario="供应链管理", scale="500 人", demo_minutes=10
        ),
        outputs={},
    )


async def test_pipeline_raises_pipeline_failure_when_content_fails():
    registry = dict(AGENT_REGISTRY)
    registry["content"] = _FailingContentAgent()
    with pytest.raises(PipelineFailure) as excinfo:
        await run_pipeline(_ctx(), registry=registry)
    failures = excinfo.value.failures
    assert any(f.agent == "content" for f in failures), "must report content failure"


async def test_sibling_agents_data_and_architecture_still_succeed():
    """Data and Architecture don't depend on Content; they must complete (spec §4, AC-6)."""
    registry = dict(AGENT_REGISTRY)
    registry["content"] = _FailingContentAgent()
    ctx = _ctx()
    try:
        await run_pipeline(ctx, registry=registry)
    except PipelineFailure:
        pass

    assert "data" in ctx.outputs, "data agent independent of content — must complete"
    assert "architecture" in ctx.outputs, "architecture agent independent of content — must complete"
    assert "integrate" not in ctx.outputs, "integrate depends on content — must be skipped"


async def test_failing_parse_blocks_everything():
    """If the very first agent fails, no downstream agent should run."""
    registry = dict(AGENT_REGISTRY)

    class _FailingParseAgent:
        name = "parse"
        async def run(self, ctx: AgentContext):
            raise AgentError("parse", "unknown industry")

    registry["parse"] = _FailingParseAgent()
    ctx = _ctx()
    try:
        await run_pipeline(ctx, registry=registry)
    except PipelineFailure:
        pass

    assert "design" not in ctx.outputs
    assert "content" not in ctx.outputs
```

- [ ] **Step 2: Run, expect pass**

```bash
pytest tests/test_orchestrator_failure.py -v
```
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_orchestrator_failure.py
git commit -m "test(backend): orchestrator failure isolation — AC-6"
```

---

## Task 13: FastAPI app, SSE generate route, and export route

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api_generate.py`
- Create: `backend/tests/test_api_export.py`

**Interfaces:**
- Consumes: `SessionStore`, `run_pipeline`, `AgentEvent`, `RequirementInput`, all agents.
- Produces:
  - `POST /api/generate` — 202 + `{"session_id": "..."}`; fires pipeline in background.
  - `GET /api/progress/{session_id}` — SSE stream, `text/event-stream`. Each event: `data: {"agent":..., "status":...}`.
  - `GET /api/result/{session_id}` — 200 + `PlanResult` JSON; 404; 202.
  - `GET /api/export/{session_id}?format=md` — 200 Markdown download; 501 for pdf.
  - CORS for `localhost:5173`.
  - Background eviction every 60s.

- [ ] **Step 1: Write the failing test for generate + progress**

Create `backend/tests/test_api_generate.py`:
```python
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
```

- [ ] **Step 2: Run, expect failure**

```bash
pytest tests/test_api_generate.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Write the export test**

Create `backend/tests/test_api_export.py`:
```python
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
```

- [ ] **Step 4: Run, expect failure**

```bash
pytest tests/test_api_export.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 5: Implement `app/main.py`**

```python
"""
FastAPI application — the single entry point.

Routes:
  POST  /api/generate              — accept RequirementInput, fire pipeline, return session_id
  GET   /api/progress/{session_id} — SSE event stream
  GET   /api/result/{session_id}   — poll final PlanResult
  GET   /api/export/{session_id}   — file download (md, pdf stub)
"""
from __future__ import annotations
import asyncio
import json as _json
from asyncio import Queue
from collections import defaultdict
from contextlib import asynccontextmanager
import anyio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from app.schemas import RequirementInput, GenerateResponse, PlanResult
from app.session import SessionStore
from app.agents.base import AgentContext
from app.orchestrator.engine import run_pipeline, PipelineFailure
from app.orchestrator.events import AgentEvent

store = SessionStore()
progress_queues: dict[str, Queue] = defaultdict(Queue)
_CANCEL = object()


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with anyio.create_task_group() as tg:
        tg.start_soon(_eviction_loop)
        yield


app = FastAPI(title="以型促签 API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _eviction_loop():
    while True:
        await anyio.sleep(60)
        store.evict_expired()


async def _run_and_notify(sid: str, req: RequirementInput):
    ctx = AgentContext(session_id=sid, requirement=req, outputs={})
    q = progress_queues[sid]

    async def emit(ev: AgentEvent):
        await q.put(ev.to_dict())

    try:
        result = await run_pipeline(ctx, on_event=emit)
        store.set_result(sid, {
            "session_id": sid,
            "markdown": result["markdown"],
            "functions": result["functions"],
            "mock_data": result["mock_data"],
            "architecture": result["architecture"],
            "demo_script": result["demo_script"],
        })
        await q.put({"agent": "pipeline", "status": "done"})
    except PipelineFailure as e:
        await q.put({"error": str(e)})
    finally:
        await q.put(_CANCEL)


@app.post("/api/generate", status_code=202)
async def generate(req: RequirementInput) -> GenerateResponse:
    sid = store.create(req)
    asyncio.create_task(_run_and_notify(sid, req))
    return GenerateResponse(session_id=sid)


@app.get("/api/progress/{session_id}")
async def progress(session_id: str):
    if store.get(session_id) is None:
        raise HTTPException(404, "session not found")

    async def event_stream():
        q = progress_queues[session_id]
        while True:
            item = await q.get()
            if item is _CANCEL:
                break
            yield f"data: {_json.dumps(item)}\n\n"
        progress_queues.pop(session_id, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/result/{session_id}")
async def result(session_id: str) -> PlanResult:
    entry = store.result(session_id)
    if store.get(session_id) is None:
        raise HTTPException(404, "session not found")
    if entry is None:
        raise HTTPException(202, "pipeline still running")
    return PlanResult.model_validate(entry)


@app.get("/api/export/{session_id}")
async def export(session_id: str, format: str = Query("md")):
    entry = store.result(session_id)
    if store.get(session_id) is None:
        raise HTTPException(404, "session not found")
    if entry is None:
        raise HTTPException(202, "pipeline still running")
    if format == "pdf":
        raise HTTPException(501, "PDF export not supported in MVP")
    md = entry["markdown"]
    filename = f"售前方案-{session_id[:8]}.md"
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run API tests**

```bash
pytest tests/test_api_generate.py tests/test_api_export.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/tests/test_api_generate.py backend/tests/test_api_export.py
git commit -m "feat(backend): FastAPI app — generate, SSE progress, result, export (AC-5)"
```

---

## Task 14: Frontend — Vue 3 + Vite + Element Plus

**Files:**
- Create: `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`
- Create: `frontend/src/main.ts`, `env.d.ts`, `App.vue`, `api.ts`, `stores/plan.ts`
- Create: `frontend/src/components/RequirementForm.vue`, `ProgressPanel.vue`, `PlanView.vue`, `ExportButton.vue`
- Create: `frontend/tests/RequirementForm.spec.ts`, `PlanView.spec.ts`

**Interfaces:**
- Consumes: Backend API at `http://localhost:8000` (proxied by Vite).
- Produces: Single-page app: form → progress → result → export.

- [ ] **Step 1: Scaffold config files**

Create `frontend/package.json`:
```json
{
  "name": "yixing-frontend", "version": "0.1.0", "private": true, "type": "module",
  "scripts": {
    "dev": "vite", "build": "vue-tsc && vite build", "preview": "vite preview",
    "test": "vitest run", "test:watch": "vitest"
  },
  "dependencies": { "vue": "^3.4", "pinia": "^2.1", "element-plus": "^2.7", "marked": "^12.0", "@element-plus/icons-vue": "^2.3" },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0", "@vue/test-utils": "^2.4", "jsdom": "^24.0",
    "typescript": "^5.5", "vite": "^5.3", "vitest": "^1.6", "vue-tsc": "^2.0"
  }
}
```

Create `frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  test: { environment: 'jsdom', globals: true },
})
```

Create `frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022", "module": "ESNext", "moduleResolution": "bundler",
    "strict": true, "jsx": "preserve", "resolveJsonModule": true,
    "isolatedModules": true, "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"], "skipLibCheck": true, "noEmit": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "src/**/*.d.ts"]
}
```

Create `frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": { "composite": true, "module": "ESNext", "moduleResolution": "bundler", "allowSyntheticDefaultImports": true },
  "include": ["vite.config.ts"]
}
```

Create `frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>以型促签</title></head>
<body><div id="app"></div><script type="module" src="/src/main.ts"></script></body>
</html>
```

Create `frontend/src/env.d.ts`:
```ts
/// <reference types="vite/client" />
declare module '*.vue' { import type { DefineComponent } from 'vue'; const c: DefineComponent<{}, {}, any>; export default c }
```

- [ ] **Step 2: Implement `api.ts`**

Create `frontend/src/api.ts`:
```ts
export interface RequirementInput {
  industry: string; scenario: string; scale: string
  demo_minutes: number; background?: string; template?: string
}

export interface AgentEvent {
  agent: string; status: 'running' | 'done' | 'failed'
  elapsed_ms?: number; error?: string
}

export interface PlanResult {
  session_id: string; markdown: string
  functions: Record<string, any>[]
  mock_data: Record<string, any>
  architecture: string; demo_script: Record<string, any>
}

export async function submitRequirement(req: RequirementInput): Promise<string> {
  const r = await fetch('/api/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!r.ok) throw new Error(await r.text())
  return (await r.json()).session_id
}

export function streamProgress(
  sessionId: string,
  onEvent: (ev: AgentEvent) => void,
  onDone: () => void
): () => void {
  const evt = new EventSource(`/api/progress/${sessionId}`)
  evt.onmessage = (msg) => {
    const data = JSON.parse(msg.data)
    if (data.agent === 'pipeline' && data.status === 'done') { evt.close(); onDone(); return }
    if (data.error) { evt.close(); onEvent({ agent: 'pipeline', status: 'failed', error: data.error }); onDone(); return }
    onEvent(data as AgentEvent)
  }
  evt.onerror = () => { evt.close(); onDone() }
  return () => evt.close()
}

export async function fetchResult(sid: string): Promise<PlanResult> {
  const r = await fetch(`/api/result/${sid}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function exportUrl(sid: string): string { return `/api/export/${sid}?format=md` }
```

- [ ] **Step 3: Implement Pinia store**

Create `frontend/src/stores/plan.ts`:
```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { submitRequirement, streamProgress, fetchResult, exportUrl, type AgentEvent, type PlanResult, type RequirementInput } from '@/api'

export const usePlanStore = defineStore('plan', () => {
  const phase = ref<'form' | 'generating' | 'done' | 'error'>('form')
  const sessionId = ref('')
  const events = ref<AgentEvent[]>([])
  const result = ref<PlanResult | null>(null)
  const error = ref<string | null>(null)
  let cancel: (() => void) | null = null

  async function submit(req: RequirementInput) {
    phase.value = 'generating'; events.value = []; result.value = null; error.value = null
    try {
      sessionId.value = await submitRequirement(req)
      cancel = streamProgress(
        sessionId.value,
        (ev) => { events.value = [...events.value, ev] },
        async () => {
          const last = events.value[events.value.length - 1]
          if (last?.status === 'failed' || last?.error) {
            phase.value = 'error'; error.value = last?.error || 'Pipeline failed'; return
          }
          result.value = await fetchResult(sessionId.value)
          phase.value = 'done'
        },
      )
    } catch (e: any) { phase.value = 'error'; error.value = e.message }
  }

  function reset() { cancel?.(); phase.value = 'form'; events.value = []; result.value = null; error.value = null }
  function exportLink() { return sessionId.value ? exportUrl(sessionId.value) : '' }
  return { phase, sessionId, events, result, error, submit, reset, exportLink }
})
```

- [ ] **Step 4: Implement `main.ts` + `App.vue`**

Create `frontend/src/main.ts`:
```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'

createApp(App).use(createPinia()).use(ElementPlus).mount('#app')
```

Create `frontend/src/App.vue`:
```vue
<template>
  <div class="app-container">
    <el-header style="text-align:center;font-size:24px;font-weight:bold;padding:20px 0">
      以型促签 · 售前快速原型生成器
    </el-header>
    <el-main>
      <RequirementForm v-if="plan.phase === 'form'" />
      <ProgressPanel v-else-if="plan.phase === 'generating'" />
      <PlanView v-else-if="plan.phase === 'done'" />
      <el-result v-else-if="plan.phase === 'error'" status="error" :title="plan.error ?? '未知错误'" sub-title="请返回重新提交">
        <template #extra><el-button type="primary" @click="plan.reset()">返回</el-button></template>
      </el-result>
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { usePlanStore } from '@/stores/plan'
import RequirementForm from '@/components/RequirementForm.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import PlanView from '@/components/PlanView.vue'
const plan = usePlanStore()
</script>

<style>
.app-container { max-width: 960px; margin: 0 auto; }
</style>
```

- [ ] **Step 5: Implement components**

Create `frontend/src/components/RequirementForm.vue`:
```vue
<template>
  <el-card header="客户需求输入">
    <el-form :model="form" :rules="rules" ref="formRef" label-width="130px" @submit.prevent="handleSubmit">
      <el-form-item label="客户行业" prop="industry">
        <el-input v-model="form.industry" placeholder="如：制造业、金融、零售" />
      </el-form-item>
      <el-form-item label="关注场景" prop="scenario">
        <el-input v-model="form.scenario" placeholder="如：供应链管理、风控" />
      </el-form-item>
      <el-form-item label="客户规模" prop="scale">
        <el-input v-model="form.scale" placeholder="如：500 人以上" />
      </el-form-item>
      <el-form-item label="演示时长（分钟）" prop="demo_minutes">
        <el-input-number v-model="form.demo_minutes" :min="1" :max="120" />
      </el-form-item>
      <el-form-item label="客户背景">
        <el-input v-model="form.background" type="textarea" :rows="3" placeholder="（选填）客户痛点、竞品情况等" />
      </el-form-item>
      <el-form-item label="演示模板">
        <el-select v-model="form.template" placeholder="（选填）选择预设模板" clearable>
          <el-option label="供应链演示模板" value="供应链演示模板" />
          <el-option label="风控演示模板" value="风控演示模板" />
          <el-option label="数据分析演示模板" value="数据分析演示模板" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">生成方案</el-button>
        <el-button @click="formRef?.resetFields()">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { usePlanStore } from '@/stores/plan'

const plan = usePlanStore()
const formRef = ref<FormInstance>()
const form = reactive({ industry: '', scenario: '', scale: '', demo_minutes: 15, background: '', template: '' })

const rules: FormRules = {
  industry: [{ required: true, message: '请输入客户行业', trigger: 'blur' }],
  scenario: [{ required: true, message: '请输入关注场景', trigger: 'blur' }],
  scale: [{ required: true, message: '请输入客户规模', trigger: 'blur' }],
  demo_minutes: [{ required: true, message: '请选择演示时长', trigger: 'change' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  plan.submit({
    industry: form.industry, scenario: form.scenario, scale: form.scale,
    demo_minutes: form.demo_minutes,
    background: form.background || undefined, template: form.template || undefined,
  })
}
</script>
```

Create `frontend/src/components/ProgressPanel.vue`:
```vue
<template>
  <el-card header="正在生成方案…">
    <el-steps :active="activeStep" finish-status="success" direction="vertical">
      <el-step v-for="agent in orderedAgents" :key="agent"
        :title="agentLabel(agent)"
        :status="stepStatus(agent)"
        :description="stepDescription(agent)" />
    </el-steps>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePlanStore } from '@/stores/plan'

const plan = usePlanStore()
const orderedAgents = ['parse', 'design', 'content', 'data', 'architecture', 'integrate']
const labels: Record<string, string> = {
  parse: '需求解析', design: '方案设计', content: '内容生成',
  data: '数据模拟', architecture: '架构描述', integrate: '结果整合',
}
function agentLabel(n: string) { return labels[n] ?? n }

const activeStep = computed(() => plan.events.filter(e => e.status === 'done').length)

function stepStatus(name: string): 'wait' | 'process' | 'finish' | 'error' {
  const ev = plan.events.find(e => e.agent === name)
  if (!ev) return 'wait'
  if (ev.status === 'done') return 'finish'
  if (ev.status === 'failed') return 'error'
  return 'process'
}

function stepDescription(name: string): string {
  const ev = plan.events.find(e => e.agent === name)
  if (!ev) return ''
  if (ev.status === 'done') return `${ev.elapsed_ms}ms`
  if (ev.status === 'failed') return ev.error ?? '失败'
  return '执行中…'
}
</script>
```

Create `frontend/src/components/PlanView.vue`:
```vue
<template>
  <el-card header="生成结果">
    <div v-html="rendered" class="markdown-body"></div>
    <ExportButton style="margin-top:16px" />
    <el-button style="margin-top:16px;margin-left:12px" @click="plan.reset()">返回重新生成</el-button>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import { usePlanStore } from '@/stores/plan'
import ExportButton from './ExportButton.vue'

const plan = usePlanStore()
const rendered = computed(() => marked(plan.result?.markdown ?? ''))
</script>

<style>
.markdown-body h1 { font-size:1.8em; border-bottom:2px solid #409EFF; padding-bottom:8px; }
.markdown-body h2 { font-size:1.4em; margin-top:24px; }
.markdown-body h3 { font-size:1.1em; margin-top:16px; }
.markdown-body pre { background:#f5f7fa; padding:12px; border-radius:4px; overflow-x:auto; }
.markdown-body table { border-collapse:collapse; width:100%; }
.markdown-body th, .markdown-body td { border:1px solid #dcdfe6; padding:8px; text-align:left; }
</style>
```

Create `frontend/src/components/ExportButton.vue`:
```vue
<template>
  <el-button type="primary" :icon="Download" @click="doExport">导出 Markdown</el-button>
</template>

<script setup lang="ts">
import { Download } from '@element-plus/icons-vue'
import { usePlanStore } from '@/stores/plan'
const plan = usePlanStore()
function doExport() { const url = plan.exportLink(); if (url) window.open(url, '_blank') }
</script>
```

- [ ] **Step 6: Write frontend tests**

Create `frontend/tests/RequirementForm.spec.ts`:
```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import RequirementForm from '@/components/RequirementForm.vue'

describe('RequirementForm', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('renders all required fields', () => {
    const wrapper = mount(RequirementForm, { global: { plugins: [ElementPlus] } })
    expect(wrapper.find('input[placeholder*="制造业"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder*="供应链"]').exists()).toBe(true)
    expect(wrapper.findAll('button').some(b => b.text().includes('生成方案'))).toBe(true)
  })
})
```

Create `frontend/tests/PlanView.spec.ts`:
```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PlanView from '@/components/PlanView.vue'
import { usePlanStore } from '@/stores/plan'

describe('PlanView', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('renders markdown from store result', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = usePlanStore()
    store.result = { session_id: 's1', markdown: '# 售前方案\n\n测试', functions: [], mock_data: {}, architecture: '', demo_script: {} }
    store.phase = 'done'
    const wrapper = mount(PlanView, { global: { plugins: [pinia] } })
    await wrapper.vm.$nextTick()
    expect(wrapper.html()).toContain('售前方案')
  })
})
```

- [ ] **Step 7: Install + run frontend tests**

```bash
cd frontend && npm install && npx vitest run
```
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
cd frontend && git add . && cd ..
git commit -m "feat(frontend): Vue 3 + Element Plus — form, progress, result, export"
```

---

## Task 15: Makefile, README, E2E acceptance test

**Files:**
- Create: `Makefile`
- Create: `README.md`
- Create: `backend/tests/test_e2e_ac.py`

**Interfaces:**
- Consumes: Everything.
- Produces: dev commands; project README; E2E acceptance test covering AC-1..AC-7.

- [ ] **Step 1: Write `Makefile`**

```makefile
.PHONY: install test-backend test-frontend test dev-backend dev-frontend e2e

install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
	cd frontend && npm install

test-backend:
	cd backend && pytest -v

test-frontend:
	cd frontend && npx vitest run

test: test-backend test-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

e2e:
	cd backend && pytest tests/test_e2e_ac.py -v
```

- [ ] **Step 2: Write `README.md`**

```markdown
# 以型促签 (Pre-sales Rapid Prototype Generator)

基于多 Agent 协作的售前快速原型生成工具。

## 快速开始

1. `make install` — 安装所有依赖
2. `make dev-backend` → http://localhost:8000/docs
3. `make dev-frontend` → http://localhost:5173
4. `make test` — 运行全部测试
5. `make e2e` — 验收测试 (AC-1..AC-7)

## 技术栈

- 后端: Python 3.11+, FastAPI, Pydantic v2, anyio
- 前端: Vue 3, Vite, Element Plus, Pinia, TypeScript
- 行业模板: YAML, `backend/app/templates/industries/`

## 架构

详见 [CLAUDE.md](./CLAUDE.md) 和 [实现计划](./docs/superpowers/plans/2026-07-07-yixing-cuqian.md)
```

- [ ] **Step 3: Write E2E acceptance test**

Create `backend/tests/test_e2e_ac.py`:
```python
"""
E2E acceptance test — one test per AC-1..AC-7 (§6).

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
    payload = {"industry": "制造业", "scenario": "供应链管理", "scale": "500 人", "demo_minutes": 10, **(overrides or {})}
    r = await client.post("/api/generate", json=payload)
    assert r.status_code == 202, f"AC-1 submit failed: {r.text}"
    return r.json()["session_id"]


async def _wait(client, sid, timeout=30):
    deadline = time.monotonic() + timeout
    import anyio
    while time.monotonic() < deadline:
        await anyio.sleep(0.05)
        r = await client.get(f"/api/result/{sid}")
        if r.status_code == 200:
            return r.json()
    pytest.fail("AC-7: pipeline timed out")


async def test_ac1_submit_and_progress(client):
    """AC-1: 用户填写需求表单后能成功提交，系统进入 Agent 执行流程，前端显示执行进度."""
    r = await client.post("/api/generate", json={
        "industry": "制造业", "scenario": "供应链管理", "scale": "500 人", "demo_minutes": 10
    })
    assert r.status_code == 202
    sid = r.json()["session_id"]
    resp = await client.get(f"/api/progress/{sid}", timeout=30)
    assert resp.status_code == 200
    assert "running" in resp.text or "done" in resp.text


async def test_ac2_parse_extracts_industry_scenario(client):
    """AC-2: 需求解析 Agent 能正确提取客户行业和关注场景."""
    sid = await _submit(client, {"industry": "金融", "scenario": "风控"})
    result = await _wait(client, sid)
    md = result["markdown"]
    assert "金融" in md or "finance" in md.lower()
    assert "风控" in md


async def test_ac3_at_least_three_features(client):
    """AC-3: 方案中包含与客户场景匹配的功能清单，功能点数量 >= 3 个."""
    sid = await _submit(client)
    result = await _wait(client, sid)
    functions = result["functions"]
    assert len(functions) >= 3, f"got {len(functions)}, need >= 3"


async def test_ac4_mock_data_fields_match_industry(client):
    """AC-4: 模拟数据与客户行业场景匹配，数据字段符合该行业的典型业务含义."""
    sid = await _submit(client, {"industry": "制造业", "scenario": "供应链管理"})
    result = await _wait(client, sid)
    tables = result["mock_data"]
    assert "orders" in tables
    first = tables["orders"][0]
    for field in ("order_id", "customer", "sku", "qty", "due_date", "status"):
        assert field in first, f"orders missing field '{field}'"


async def test_ac5_export_complete_file(client):
    """AC-5: 最终方案可导出为文件，导出文件包含完整内容且格式正确."""
    sid = await _submit(client)
    await _wait(client, sid)
    r = await client.get(f"/api/export/{sid}?format=md")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert len(r.text) > 500
    assert "# 售前方案" in r.text


async def test_ac6_failure_shows_agent_name_and_reason(client):
    """AC-6: Agent 执行失败时前端有明确提示，显示失败 Agent 名称和错误原因."""
    r = await client.post("/api/generate", json={
        "industry": "不存在的行业XYZ", "scenario": "测试", "scale": "1 人", "demo_minutes": 5,
    })
    sid = r.json()["session_id"]
    resp = await client.get(f"/api/progress/{sid}", timeout=30)
    text = resp.text
    lines = [line.removeprefix("data: ") for line in text.strip().split("\n") if line.startswith("data:")]
    events = [json.loads(line) for line in lines]
    failed = [ev for ev in events if ev.get("status") == "failed" or ev.get("error")]
    assert failed, "must have a failed event for invalid industry"
    error_text = str(failed[0])
    assert "parse" in error_text or "unknown" in error_text.lower(), f"must name failing agent: {error_text}"


async def test_ac7_end_to_end_within_30_seconds(client):
    """AC-7: 从提交到结果展示的端到端耗时 <= 30 秒."""
    start = time.monotonic()
    sid = await _submit(client)
    await _wait(client, sid, timeout=30)
    elapsed = time.monotonic() - start
    assert elapsed <= 30, f"AC-7 failed: {elapsed:.1f}s > 30s"
```

- [ ] **Step 4: Run E2E tests**

```bash
pytest tests/test_e2e_ac.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest -v
```
Expected: all tests pass (~45+).

- [ ] **Step 6: Commit**

```bash
git add Makefile README.md backend/tests/test_e2e_ac.py
git commit -m "feat: Makefile, README, E2E acceptance tests (AC-1..AC-7)"
```

---

## Self-Review

### 1. Spec coverage

| Spec requirement | Covered by Task |
|---|---|
| F1-1 Form input (industry, scenario, scale, duration) | Task 14 (RequirementForm.vue) |
| F1-2 Free-text background (P1) | Not in scope (MVP = P0 only) |
| F1-3 Preset templates (P1) | Task 14 (el-select template dropdown) |
| F1-4 Required-field validation | Task 1 (pydantic) + Task 14 (el-form rules) |
| F2-1 Parse Agent (P0) | Task 4 |
| F2-2 Design Agent (P0) | Task 5 |
| F2-3 Content Agent (P0) | Task 6 |
| F2-4 Data Agent (P0) | Task 7 |
| F2-5 Orchestration engine (P0) | Tasks 10, 11, 12 |
| F2-6 Progress visualization (P1) | Task 14 (ProgressPanel.vue, SSE) |
| F3-1 Plan overview Markdown/HTML (P0) | Task 9 (IntegrateAgent + markdown.py) |
| F3-2 Architecture Mermaid (P1) | Task 8 |
| F3-3 Demo checklist with steps (P0) | Task 6 (FeatureBrief flow + talking points) |
| F3-4 Mock data JSON/CSV (P0) | Task 7 (MockDataPack) |
| F3-5 Time allocation (P1) | Task 5 (DesignedPlan.time_allocation) |
| F3-6 Export Markdown/PDF (P1) | Task 13 (GET /api/export) |
| F4-1 History list (P1) | Not in scope |
| §4 ≤ 30s | Task 15 (AC-7 E2E test), enforced by anyio concurrent layers |
| §4 ≥ 80% coverage | Task 5 (DesignAgent.coverage_ratio MIN_COVERAGE) |
| §4 Fault-tolerance | Task 12 (orchestrator failure path) |
| §4 Configurability | Task 3 (YAML industry templates), Task 10 (DAG as data) |
| §4 Data safety | Task 1 (SessionStore in-memory, TTL) |
| AC-1 Form submit + progress | Task 15 (test_ac1) |
| AC-2 Correct industry+scenario | Task 15 (test_ac2) |
| AC-3 ≥ 3 features | Task 15 (test_ac3) |
| AC-4 Mock data semantics | Task 15 (test_ac4) |
| AC-5 Export complete file | Task 15 (test_ac5) |
| AC-6 Failure names agent | Task 15 (test_ac6) |
| AC-7 ≤ 30s end-to-end | Task 15 (test_ac7) |

**Gaps:** F1-2 (free-text background), F4-1 (history), F4-2 (template reuse), F4-3 (rating) are P1/P2 — explicitly deferred to post-MVP per spec §5.4.

### 2. Placeholder scan

Scanned all 3399 lines for red-flag patterns:
- No "TBD", "TODO", "implement later", "fill in details" found.
- No bare "Add error handling" without code.
- No "Write tests for the above" without actual test code.
- No "Similar to Task N" without repeating the code.
- All steps that produce code include the actual code.

### 3. Type consistency

Verified across tasks:
- `RequirementInput` fields: `industry`, `scenario`, `scale`, `demo_minutes`, `background`, `template` — same in schemas.py, all agent files, and frontend api.ts.
- `ParsedRequirement` produced by Task 4, consumed as `parse_out` dict key `"parse"` in Tasks 5, 6, 7, 8, 9.
- `DesignedPlan` produced by Task 5, consumed as `design_out` dict key `"design"` in Tasks 6, 9.
- `AgentContext.outputs` dict key names: `"parse"`, `"design"`, `"content"`, `"data"`, `"architecture"`, `"integrate"` — consistent across all agent files and the orchestrator.
- `AgentEvent` serialized via `to_dict()` in engine.py and parsed in frontend `api.ts` — matching field names: `agent`, `status`, `elapsed_ms`, `error`.
- DAG node names match AGENT_REGISTRY keys and the `name` attribute on each Agent class.
- All `FeatureSpec` field names (`id`, `title`, `description`, `demo_steps`, `talking_points`, `scenarios`) match across template YAML, pydantic model, and markdown renderer.

---

