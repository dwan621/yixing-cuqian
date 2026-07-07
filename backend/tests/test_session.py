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
