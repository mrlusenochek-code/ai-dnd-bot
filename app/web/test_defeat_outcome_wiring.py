import asyncio
from dataclasses import dataclass

import app.web.server as server
from app.web.server import COMBAT_STATE_KEY, _grant_defeat_outcome_once


@dataclass
class _FakeSession:
    settings: dict


def test_grant_defeat_outcome_once_stores_payload_and_is_idempotent(monkeypatch) -> None:
    started_at = "2026-03-01T10:00:00+00:00"
    sess = _FakeSession(settings={COMBAT_STATE_KEY: {"started_at_iso": started_at}})
    patch = {
        "status": "Бой завершён",
        "lines": [{"text": "Поражение: герои разбиты"}],
    }

    events: list[str] = []

    async def _fake_add_system_event(_db, _sess, text, **_kwargs):
        events.append(text)

    monkeypatch.setattr(server, "flag_modified", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "add_system_event", _fake_add_system_event)

    first = asyncio.run(_grant_defeat_outcome_once(None, sess, patch))
    second = asyncio.run(_grant_defeat_outcome_once(None, sess, patch))

    assert first is True
    assert second is False
    assert sess.settings["combat_defeat_outcome_for"] == started_at
    assert sess.settings["combat_defeat_outcome"]["started_at_iso"] == started_at
    assert sess.settings["combat_defeat_outcome"]["key"] == "enemies_withdraw"
    assert len(events) == 1
