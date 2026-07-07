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
from urllib.parse import quote
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
    safe_name = quote(filename)
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
