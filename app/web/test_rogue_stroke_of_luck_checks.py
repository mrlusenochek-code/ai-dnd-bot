from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.db.models import Character
from app.web import gm_orchestrator, ws_handlers


def _rogue_stroke_of_luck_features(*, used: bool = False) -> dict:
    runtime = {"stroke_of_luck_used": True} if used else {}
    return {
        "features": [
            {
                "key": "stroke_of_luck",
                "mechanics": {
                    "type": "stroke_of_luck",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                    "attack_miss_to_hit": True,
                    "failed_check_d20_to_20": True,
                },
            }
        ],
        "runtime": runtime,
    }


def _character(*, used: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Плут",
        level=20,
        class_features=_rogue_stroke_of_luck_features(used=used),
    )


def test_manual_failed_skillcheck_creates_pending_and_stroke_of_luck_turns_roll_into_20() -> None:
    ch = _character()

    marked = ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        ch,
        kind="skill",
        name="stealth",
        dc=15,
        old_roll=7,
        old_total=11,
        mod=4,
        mode="normal",
        actor_uid=1,
        source="manual_check",
    )
    assert marked is True
    pending = ws_handlers._get_stroke_of_luck_check_pending(ch)
    assert pending["name"] == "stealth"
    assert pending["old_roll"] == 7
    assert pending["mod"] == 4

    payload, err, changed = ws_handlers._apply_stroke_of_luck_failed_check(ch)
    assert err is None
    assert changed is True
    assert payload is not None
    assert payload["new_roll"] == 20
    assert payload["new_total"] == 24
    assert payload["success"] is True
    runtime_after = (ch.class_features or {}).get("runtime") or {}
    assert runtime_after.get("stroke_of_luck_used") is True
    assert "stroke_of_luck_pending_failed_check" not in runtime_after


def test_toolcheck_pending_and_even_d20_20_can_still_fail() -> None:
    ch = _character()

    marked = ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        ch,
        kind="tool",
        name="thieves_tools",
        dc=20,
        old_roll=4,
        old_total=3,
        mod=-1,
        mode="normal",
        actor_uid=1,
        source="manual_check",
    )
    assert marked is True

    payload, err, _changed = ws_handlers._apply_stroke_of_luck_failed_check(ch)
    assert err is None
    assert payload is not None
    assert payload["new_total"] == 19
    assert payload["success"] is False


def test_attack_use_blocks_check_use_and_success_does_not_create_pending() -> None:
    used_ch = _character(used=True)
    assert ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        used_ch,
        kind="skill",
        name="stealth",
        dc=15,
        old_roll=7,
        old_total=11,
        mod=4,
        mode="normal",
    ) is False

    fresh_ch = _character()
    assert ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        fresh_ch,
        kind="skill",
        name="stealth",
        dc=15,
        old_roll=15,
        old_total=19,
        mod=4,
        mode="normal",
    ) is False
    assert ws_handlers._get_stroke_of_luck_check_pending(fresh_ch) == {}


def test_reliable_talent_order_and_save_death_save_rejection() -> None:
    ch = _character()
    assert ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        ch,
        kind="skill",
        name="stealth",
        dc=15,
        old_roll=10,
        old_total=14,
        mod=4,
        mode="normal",
    ) is True
    payload, err, _changed = ws_handlers._apply_stroke_of_luck_failed_check(ch)
    assert err is None
    assert payload is not None
    assert payload["old_roll"] == 10
    assert payload["new_total"] == 24

    rejected = _character()
    assert ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        rejected,
        kind="save",
        name="wis",
        dc=15,
        old_roll=7,
        old_total=11,
        mod=4,
        mode="normal",
    ) is False
    assert ws_handlers._maybe_mark_stroke_of_luck_failed_check_pending(
        rejected,
        kind="death_save",
        name="death_save",
        dc=10,
        old_roll=7,
        old_total=7,
        mod=0,
        mode="normal",
    ) is False


def test_gm_failed_skill_check_creates_pending(monkeypatch) -> None:
    events: list[str] = []

    async def _fake_add_system_event(_db, _sess, message: str, **_kwargs) -> None:
        events.append(message)

    monkeypatch.setattr(gm_orchestrator, "add_system_event", _fake_add_system_event)

    ch = Character(
        session_id=uuid.uuid4(),
        player_id=uuid.uuid4(),
        name="Плут",
        level=20,
        class_features=_rogue_stroke_of_luck_features(),
        stats={},
    )
    changed = asyncio.run(
        gm_orchestrator._mark_stroke_of_luck_pending_from_check_results(
            None,
            SimpleNamespace(),
            {1: ch},
            [
                {
                    "actor_uid": 1,
                    "kind": "skill",
                    "name": "stealth",
                    "dc": 15,
                    "roll": 9,
                    "total": 13,
                    "mode": "normal",
                }
            ],
        )
    )

    assert changed is True
    pending = (ch.class_features or {}).get("runtime", {}).get("stroke_of_luck_pending_failed_check") or {}
    assert pending.get("source") == "gm_check"
    assert pending.get("name") == "stealth"
    assert events and "Удачный удар" in events[0]
