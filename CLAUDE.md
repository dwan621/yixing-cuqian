# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build / Test / Run

All commands assume Python 3.11+ and Node 20+.

```bash
# Install everything
make install                        # venv + pip install -e ".[dev]" + npm install

# Backend (Python/FastAPI)
cd backend && pytest -v             # 74 tests
cd backend && pytest -k <name> -v   # single test
cd backend && pytest tests/test_e2e_ac.py -v   # AC-1..AC-7 (7 tests)

# Frontend (Vue 3/Vite)
cd frontend && npx vitest run       # 2 tests

# Dev servers
make dev-backend                    # http://localhost:8800 (template mode)
make dev-frontend                   # http://localhost:3300
LLM_MODE=llm make dev-backend       # LLM mode
```

## Architecture

```
frontend/                          # Vue 3 + Vite + Element Plus + Pinia
  src/
    api.ts                         # fetch + SSE wrappers (sole network surface)
    stores/plan.ts                 # state machine: form -> generating -> done | error
    components/
      RequirementForm.vue          # F1-1..F1-4
      ProgressPanel.vue            # F2-6 (SSE progress)
      PlanView.vue                 # F3-1 (marked + DOMPurify)
      ExportButton.vue             # F3-6

backend/                           # Python + FastAPI
  app/
    main.py                        # POST /generate, GET /progress (SSE), /result, /export
    schemas.py                     # RequirementInput, GenerateResponse, PlanResult
    session.py                     # In-memory SessionStore (TTL 900s, zero disk writes)
    agents/
      base.py                      # Agent Protocol, AgentContext, AgentError
      registry.py                  # AGENT_REGISTRY: LLM_MODE switch (template/llm/hybrid)
      parse_agent.py               # F2-1 template
      design_agent.py              # F2-2 template
      content_agent.py             # F2-3 template
      data_agent.py                # F2-4 template
      architecture_agent.py        # template (Mermaid)
      integrate_agent.py           # 结果整合 + render_markdown()
      llm/
        client.py                  # AsyncOpenAI wrapper for Volcengine Ark
        base.py                    # LLMAgentBase + HybridAgent + _fix_llm_json()
        prompts.py                 # 6 four-section prompt builders
        parse_agent.py             # LLMParseAgent (LLM-driven)
        design_agent.py            # LLMDesignAgent
        content_agent.py           # LLMContentAgent
        data_agent.py              # LLMDataAgent
        architecture_agent.py      # LLMArchitectureAgent
    orchestrator/
      dag.py                       # DAG definition (data-only, config-driven)
      engine.py                    # run_pipeline(): layers + anyio concurrency
      events.py                    # AgentEvent dataclass
    templates/industries/
      manufacturing.yaml, finance.yaml, retail.yaml   # 6 features each, 3 mock tables
    export/markdown.py             # render_markdown(): 6-section document assembler
```

### Agent DAG

```
parse                     (layer 0)
  +-- design              (layer 1)
  |     +-- content       (layer 2, || data)
  |     +-- data          (layer 2, || content)
  +-- architecture        (layer 1, || design)
        |
     integrate            (layer 3, blocks on content+data+architecture)
```

Layers run sequentially; nodes within a layer run concurrently via `anyio.create_task_group`. Single agent failure raises `AgentError` with name + reason (AC-6); sibling agents continue. All inter-agent communication goes through `ctx.outputs` dict — no shared bus.

### LLM mode

`LLM_MODE` env var (default: `template`) controls the agent registry:
- `template` — YAML/template logic, no API key needed
- `llm` — 5 agents use Volcengine Ark LLM; integrate stays template (pure assembly, not LLM-friendly)
- `hybrid` — LLM first, auto fallback to template on `AgentError`

API config in `backend/.env` (git-ignored). See `.env.example`:
```
ARK_API_KEY=your-key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/plan/v3
ARK_MODEL=ark-code-latest
LLM_MODE=llm
```

LLM agents follow the same `Agent` Protocol — the engine doesn't know which is which. Adding a new LLM agent: write the class, add to `_llm_registry()` in `registry.py`.

## Key constraints (spec §4, enforced in code)

- **<=30s e2e** — template ~1s, LLM ~55s (acceptable for external API)
- **Fault tolerance** — `AgentError` percolates; engine skips downstream, siblings finish (AC-6)
- **Configurability** — new industry = drop YAML; new agent = edit DAG tuple + registry
- **Data safety** — `SessionStore` is plain `dict`, zero disk I/O, 15-min TTL
- **Coverage >= 80%** — `DesignAgent` enforces `MIN_COVERAGE = 0.8`

## Working conventions

- Import pydantic models from the template agent file, don't redefine (e.g. `from app.agents.parse_agent import ParsedRequirement`)
- Every agent docstring: 角色定义 · 输入格式 · 输出格式 · 约束条件 (spec §5.3)
- Every `run()`: read from `ctx.requirement`/`ctx.outputs`, write `ctx.outputs[self.name] = result.model_dump()`
- Raise `AgentError(self.name, "reason")` on controlled failure; let unexpected exceptions propagate
- `AGENT_REGISTRY` is the single swap point — never reference agent class names directly in engine or DAG
