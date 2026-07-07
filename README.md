# 以型促签 (Pre-sales Rapid Prototype Generator)

基于多 Agent 协作的售前快速原型生成工具。

## 快速开始

1. `make install` — 安装所有依赖
2. `make dev-backend` -> http://localhost:8000/docs
3. `make dev-frontend` -> http://localhost:5173
4. `make test` — 运行全部测试
5. `make e2e` — 验收测试 (AC-1..AC-7)

## 技术栈

- 后端: Python 3.11+, FastAPI, Pydantic v2, anyio
- 前端: Vue 3, Vite, Element Plus, Pinia, TypeScript
- 行业模板: YAML, `backend/app/templates/industries/`

## 架构

详见 [CLAUDE.md](./CLAUDE.md) 和 [实现计划](./docs/superpowers/plans/2026-07-07-yixing-cuqian.md)
