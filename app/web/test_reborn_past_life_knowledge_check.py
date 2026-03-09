from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _reborn_character(*, uses_used: int = 0, armed: bool = False):
    return SimpleNamespace(
        level=5,
        race_features={
            "features": {
                "knowledge_from_a_past_life": {
                    "dice": "1d6",
                    "timing": "after_seeing_d20",
                    "uses": "per_long_rest",
                    "uses_formula": "proficiency_bonus",
                }
            },
            "runtime": {
                "knowledge_past_life_uses_used": uses_used,
                "knowledge_past_life_armed": armed,
            },
        },
    )


def test_reborn_past_life_pending_apply_and_long_rest_reset(monkeypatch) -> None:
    ch = _reborn_character()

    marked = ws_handlers._reborn_mark_past_life_pending(
        session_id="reborn_pending_check",
        player_uid=None,
        ch=ch,
        dc=15,
        total=11,
        skill_key="history",
    )
    assert marked is True

    monkeypatch.setattr(ws_handlers.random, "randint", lambda _a, _b: 4)
    err, msg, changed = ws_handlers._apply_or_arm_reborn_past_life_knowledge(
        session_id="reborn_pending_check",
        player_uid=None,
        ch=ch,
    )

    assert err is None
    assert changed is True
    assert msg is not None and "+1d6 (4)" in msg and "15" in msg

    runtime = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime.get("knowledge_past_life_uses_used") or 0) == 1
    assert "knowledge_from_a_past_life_pending" not in runtime
    assert bool(runtime.get("knowledge_past_life_armed")) is False

    reset_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime_after_reset.get("knowledge_past_life_uses_used") or 0) == 0
    assert "knowledge_from_a_past_life_pending" not in runtime_after_reset
    assert "knowledge_past_life_armed" not in runtime_after_reset


def test_reborn_past_life_arm_for_next_skill_check_and_exhaustion(monkeypatch) -> None:
    ch = _reborn_character()

    err, msg, changed = ws_handlers._apply_or_arm_reborn_past_life_knowledge(
        session_id="reborn_arm_check",
        player_uid=None,
        ch=ch,
    )
    assert err is None
    assert changed is True
    assert msg is not None and "Следующая проверка навыка" in msg

    monkeypatch.setattr(ws_handlers.random, "randint", lambda _a, _b: 5)
    bonus, bonus_text, consumed = ws_handlers._consume_reborn_past_life_for_skill_check(ch, kind="skill")
    assert consumed is True
    assert bonus == 5
    assert bonus_text is not None and "5" in bonus_text

    runtime = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime.get("knowledge_past_life_uses_used") or 0) == 1
    assert bool(runtime.get("knowledge_past_life_armed")) is False

    exhausted = _reborn_character(uses_used=3, armed=False)
    err2, msg2, changed2 = ws_handlers._apply_or_arm_reborn_past_life_knowledge(
        session_id="reborn_arm_check",
        player_uid=None,
        ch=exhausted,
    )
    assert changed2 is False
    assert msg2 is None
    assert err2 is not None and "долгого отдыха" in err2
