import asyncio
from types import SimpleNamespace

from app.web import ws_handlers


def test_kickoff_lore_finalize_schedules_once_for_stuck_lore(monkeypatch):
    scheduled = []

    async def _dummy_run_lore_generation(_session_id: str):
        return None

    def _fake_create_task(coro):
        scheduled.append(coro)
        return SimpleNamespace()

    monkeypatch.setattr(ws_handlers.gm_orchestrator, "run_lore_generation", _dummy_run_lore_generation)
    monkeypatch.setattr(ws_handlers.asyncio, "create_task", _fake_create_task)
    ws_handlers._LORE_PENDING_TASKS.clear()

    sess = SimpleNamespace(
        settings={
            "lore_text": "intro",
            "lore_generated": True,
            "lore_posted": False,
        }
    )

    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is True
    assert len(scheduled) == 1
    scheduled[0].close()


def test_kickoff_lore_finalize_noop_when_lore_already_posted(monkeypatch):
    scheduled = []

    async def _dummy_run_lore_generation(_session_id: str):
        return None

    def _fake_create_task(coro):
        scheduled.append(coro)
        return SimpleNamespace()

    monkeypatch.setattr(ws_handlers.gm_orchestrator, "run_lore_generation", _dummy_run_lore_generation)
    monkeypatch.setattr(ws_handlers.asyncio, "create_task", _fake_create_task)
    ws_handlers._LORE_PENDING_TASKS.clear()

    sess = SimpleNamespace(
        settings={
            "lore_text": "intro",
            "lore_generated": True,
            "lore_posted": True,
        }
    )

    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is False
    assert scheduled == []


def test_kickoff_lore_finalize_restarts_generation_for_pending_lore(monkeypatch):
    scheduled = []

    async def _dummy_run_lore_generation(_session_id: str):
        return None

    def _fake_create_task(coro):
        scheduled.append(coro)
        return SimpleNamespace()

    monkeypatch.setattr(ws_handlers.gm_orchestrator, "run_lore_generation", _dummy_run_lore_generation)
    monkeypatch.setattr(ws_handlers.asyncio, "create_task", _fake_create_task)
    ws_handlers._LORE_PENDING_TASKS.clear()

    sess = SimpleNamespace(
        settings={
            "phase": "lore_pending",
            "story": {"story_configured": True},
            "lore_text": "",
            "lore_generated": False,
            "lore_posted": False,
        }
    )

    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is True
    assert len(scheduled) == 1
    scheduled[0].close()
    ws_handlers._LORE_PENDING_TASKS.clear()


def test_kickoff_lore_finalize_does_not_duplicate_inflight_task(monkeypatch):
    scheduled = []

    async def _dummy_run_lore_generation(_session_id: str):
        return None

    def _fake_create_task(coro):
        scheduled.append(coro)
        return SimpleNamespace()

    monkeypatch.setattr(ws_handlers.gm_orchestrator, "run_lore_generation", _dummy_run_lore_generation)
    monkeypatch.setattr(ws_handlers.asyncio, "create_task", _fake_create_task)
    ws_handlers._LORE_PENDING_TASKS.clear()

    sess = SimpleNamespace(
        settings={
            "phase": "lore_pending",
            "story": {"story_configured": True},
            "lore_text": "",
            "lore_generated": False,
            "lore_posted": False,
        }
    )

    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is True
    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is False
    assert len(scheduled) == 1
    scheduled[0].close()
    ws_handlers._LORE_PENDING_TASKS.clear()


def test_auto_recover_lore_pending_on_connect_restarts_generation(monkeypatch):
    sess = SimpleNamespace(
        settings={
            "phase": "lore_pending",
            "story": {"story_configured": True},
            "lore_text": "",
            "lore_generated": False,
            "lore_posted": False,
        }
    )
    db_token = object()
    calls = []

    class _FakeDbContext:
        async def __aenter__(self):
            return db_token

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_get_session(db, session_id):
        calls.append(("get_session", db, session_id))
        return sess

    def _fake_kickoff(session_id, loaded_sess):
        calls.append(("kickoff", session_id, loaded_sess))
        return True

    monkeypatch.setattr(ws_handlers, "AsyncSessionLocal", _FakeDbContext)
    monkeypatch.setattr(ws_handlers, "get_session", _fake_get_session)
    monkeypatch.setattr(ws_handlers, "_kickoff_lore_finalize_if_needed", _fake_kickoff)

    assert asyncio.run(ws_handlers._auto_recover_lore_pending_on_connect("s1")) is True
    assert calls == [
        ("get_session", db_token, "s1"),
        ("kickoff", "s1", sess),
    ]


def test_auto_recover_lore_pending_on_connect_keeps_existing_finalize_path(monkeypatch):
    sess = SimpleNamespace(
        settings={
            "phase": "lore_pending",
            "story": {"story_configured": True},
            "lore_text": "intro",
            "lore_generated": True,
            "lore_posted": False,
        }
    )
    db_token = object()
    calls = []

    class _FakeDbContext:
        async def __aenter__(self):
            return db_token

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_get_session(db, session_id):
        calls.append(("get_session", db, session_id))
        return sess

    def _fake_kickoff(session_id, loaded_sess):
        calls.append(("kickoff", session_id, loaded_sess))
        return True

    monkeypatch.setattr(ws_handlers, "AsyncSessionLocal", _FakeDbContext)
    monkeypatch.setattr(ws_handlers, "get_session", _fake_get_session)
    monkeypatch.setattr(ws_handlers, "_kickoff_lore_finalize_if_needed", _fake_kickoff)

    assert asyncio.run(ws_handlers._auto_recover_lore_pending_on_connect("s1")) is True
    assert calls == [
        ("get_session", db_token, "s1"),
        ("kickoff", "s1", sess),
    ]
