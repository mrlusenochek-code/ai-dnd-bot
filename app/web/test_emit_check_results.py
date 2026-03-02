from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.web import server


def test_build_check_results_system_text_contains_roll_summary() -> None:
    text = server._build_check_results_system_text(
        [
            {
                "actor_uid": 2,
                "name": "perception",
                "dc": 15,
                "roll": 14,
                "mod": 3,
                "total": 17,
                "success": True,
                "mode": "normal",
            }
        ]
    )
    assert text.startswith("🎲 #2 perception:")
    assert "d20=14" in text
    assert "итог 17 vs DC 15" in text
    assert "успех" in text


def test_emit_check_results_skips_when_flag_off(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_add_system_event(_db, _sess, text, **_kwargs):
        calls.append(str(text))

    monkeypatch.setenv("GM_SHOW_CHECK_RESULTS", "0")
    monkeypatch.setattr(server, "add_system_event", fake_add_system_event)
    asyncio.run(
        server._emit_check_results_if_enabled(
            SimpleNamespace(),
            SimpleNamespace(),
            [
                {
                    "actor_uid": 1,
                    "name": "stealth",
                    "dc": 12,
                    "roll": 9,
                    "mod": 4,
                    "total": 13,
                    "success": True,
                    "mode": "normal",
                }
            ],
        )
    )
    assert calls == []


def test_emit_check_results_emits_when_flag_on(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_add_system_event(_db, _sess, text, **_kwargs):
        calls.append(str(text))

    monkeypatch.setenv("GM_SHOW_CHECK_RESULTS", "1")
    monkeypatch.setattr(server, "add_system_event", fake_add_system_event)
    asyncio.run(
        server._emit_check_results_if_enabled(
            SimpleNamespace(),
            SimpleNamespace(),
            [
                {
                    "actor_uid": 1,
                    "name": "stealth",
                    "dc": 12,
                    "roll": 9,
                    "mod": 4,
                    "total": 13,
                    "success": True,
                    "mode": "normal",
                }
            ],
        )
    )
    assert len(calls) == 1
    assert calls[0].startswith("🎲")
    assert "stealth" in calls[0]
