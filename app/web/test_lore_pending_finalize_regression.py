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

    sess = SimpleNamespace(
        settings={
            "lore_text": "intro",
            "lore_generated": True,
            "lore_posted": True,
        }
    )

    assert ws_handlers._kickoff_lore_finalize_if_needed("s1", sess) is False
    assert scheduled == []
