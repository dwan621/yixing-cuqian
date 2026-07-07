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
