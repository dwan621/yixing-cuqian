# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repo currently contains **only the requirements spec** — `doc/02-以型促签.docx` — and no source code. The spec describes a校招生 Agent 开发作业 (campus-recruit Agent development assignment). Before writing code, read the spec (via `python C:/Users/11481/.claude/skills/docx/scripts/office/unpack.py doc/02-以型促签.docx <out>/` and extract `w:t` from `word/document.xml`, since `pandoc` is not installed on this machine).

Do not invent build/test/lint commands until the scaffold exists. When scaffolding starts, replace this section with real commands.

## Product target (from `doc/02-以型促签.docx` v1.0, 2026-07-06)

**「以型促签」/ Pre-sales Rapid Prototype Generator** — a multi-Agent tool for pre-sales engineers. User inputs a customer scenario (industry / focus / scale / desired demo length); a chain of LLM Agents produces a customized pre-sales package (functional list, mock data, demo script, optional architecture diagram) in ≤ 30 s end-to-end.

### Agent topology (spec §5.2 — the core architecture)

```
用户输入
  ↓
[需求解析 Agent]      → 结构化需求 (industry, scenario, scale)
  ↓
[方案设计 Agent]      → 功能清单
  ↓
  ├─→ [内容生成 Agent]   → 功能介绍 / 操作流程 / 价值说明 / 话术
  ├─→ [数据模拟 Agent]   → 行业匹配的 JSON / CSV mock data
  └─→ [架构描述 Agent]   → 文字描述 or Mermaid
  ↓
[结果整合 Agent]      → 最终 Markdown / HTML 方案
```

The **编排引擎** (orchestration engine, F2-5) is the piece that owns this DAG: it fixes the execution order and threads each upstream agent's output into the downstream agent's prompt. The three middle agents (内容/数据/架构) are independent given 方案设计's output — the spec draws them as fan-out, so running them concurrently is a natural fit for the ≤ 30 s budget, though the spec itself doesn't mandate it. Results converge in 结果整合. Progress must be visible to the front-end (F2-6).

### Module split (from spec §3)

| Module | Key requirements |
|---|---|
| 需求输入 (§3.1) | Form: industry, scenario, scale, demo length (P0); free-text customer background (P1); preset templates (P1); required-field validation (P0). |
| Agent 编排 (§3.2) | The 5-agent DAG above. F2-1..F2-5 are all P0. |
| 原型输出 (§3.3) | Markdown/HTML overview (P0); demo checklist with 步骤 + 话术 (P0); JSON/CSV mock data pack (P0); Mermaid architecture (P1); per-feature time allocation for the chosen demo length (P1); export Markdown/PDF (P1). |
| 方案管理 (§3.4) | History list (P1); reuse-as-template (P2); rating/feedback (P2). |

### Non-functional (§4) — enforce in code

- **≤ 30 s** end-to-end wall clock from submit to fully rendered plan.
- **Coverage**: generated 功能清单 covers ≥ 80 % of scenario-relevant features.
- **Fault-tolerance**: a single Agent failure must yield a clear error naming the failing Agent, without killing sibling Agents that can still run.
- **Configurability**: templates and per-Agent capabilities must be swappable — new industry templates are added without code changes to the orchestration engine.
- **Data safety**: customer input is session-scoped only. **Do not persist and do not exfiltrate** — this is an explicit spec constraint.

### Acceptance criteria (§6) — treat as the test matrix

AC-1 form submit → progress shown · AC-2 parsed 需求 has correct industry+scenario · AC-3 ≥ 3 scenario-relevant features · AC-4 mock-data fields match industry semantics · AC-5 export produces a complete, well-formatted file · AC-6 failure surfaces Agent name + reason · AC-7 end-to-end ≤ 30 s.

### Recommended stack (§5.1) — spec's suggestion, not a hard mandate

- Front-end: **Vue 3 + Element Plus** (form + result view + progress).
- Back-end: **Python + FastAPI** (owns the 编排引擎).
- LLM: pluggable — GLM / Claude / GPT via API.
- Agent-to-Agent communication: chained function calls, upstream output → downstream prompt (no shared bus).

### MVP order (§5.4) — build in this sequence

1. Form (industry + scenario + scale).
2. Orchestration engine with **3 agents in series** (parse → design → generate).
3. One end-to-end Markdown output.
4. Front-end display + export.
5. **Rules/templates first, real LLM later** — the spec explicitly permits mocking agents with templates to validate the pipeline before wiring in LLM calls. Preserve this seam when building.

Bonus/加分 items (§7) — multi-turn refinement, Mermaid auto-render, interactive HTML prototype, CRM import, one-click PPT (python-pptx), dynamic (LLM-decided) agent ordering. Do not pursue these before the MVP passes AC-1..AC-7.

## Working conventions specific to this repo

- **The spec is the source of truth.** When code and `doc/02-以型促签.docx` disagree, quote the spec section (e.g. "spec §3.2 F2-5") in the discussion and reconcile before editing.
- **Prompt design (§5.3):** every Agent's prompt must state — 角色定义 · 输入格式 · 输出格式 · 约束条件. Keep prompts in a dedicated `prompts/` directory (one file per Agent) once code exists, so they can be versioned and diffed independently from Python logic.
- **The orchestration engine is a DAG, not a script.** Wire it so a new agent can be inserted between existing ones by editing a config, not by editing the runner — this is what makes §4 可配置性 achievable.
- **Progress reporting is a first-class output**, not a debug log — F2-6 and AC-1 both depend on the front-end seeing per-agent state.
