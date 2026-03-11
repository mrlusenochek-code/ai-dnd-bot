from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def _reborn_character(*, level: int = 5, uses_used: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
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
                "knowledge_past_life_armed": False,
            },
        },
    )


def test_reborn_past_life_bonus_applies_to_ability_skill_and_tool_checks() -> None:
    for kind in ("ability", "skill", "tool"):
        ch = _reborn_character(level=5, uses_used=0)
        bonus, bonus_text, uses_text, changed, err = ws_handlers._consume_reborn_past_life_bonus_for_check(
            ch,
            requested=True,
            kind=kind,
            rng=_FixedRng(4),
        )

        assert err is None
        assert changed is True
        assert bonus == 4
        assert bonus_text == "Knowledge from a Past Life 1d6(4)"
        assert uses_text == "Осталось использований: 2/3"
        runtime = (ch.race_features or {}).get("runtime") or {}
        assert int(runtime.get("knowledge_past_life_uses_used") or 0) == 1


def test_reborn_past_life_rejects_non_reborn_character() -> None:
    ch = SimpleNamespace(level=5, race_features={"features": {}, "runtime": {}})

    bonus, bonus_text, uses_text, changed, err = ws_handlers._consume_reborn_past_life_bonus_for_check(
        ch,
        requested=True,
        kind="skill",
        rng=_FixedRng(3),
    )

    assert bonus == 0
    assert bonus_text == ""
    assert uses_text == ""
    assert changed is False
    assert err is not None and "недоступны" in err.lower()


def test_reborn_past_life_uses_follow_pb_and_reset_only_on_long_rest() -> None:
    ch = _reborn_character(level=5, uses_used=0)

    for _ in range(3):
        bonus, _bonus_text, _uses_text, changed, err = ws_handlers._consume_reborn_past_life_bonus_for_check(
            ch,
            requested=True,
            kind="skill",
            rng=_FixedRng(2),
        )
        assert err is None
        assert changed is True
        assert bonus == 2

    bonus, bonus_text, uses_text, changed, err = ws_handlers._consume_reborn_past_life_bonus_for_check(
        ch,
        requested=True,
        kind="ability",
        rng=_FixedRng(2),
    )
    assert bonus == 0
    assert bonus_text == ""
    assert uses_text == ""
    assert changed is False
    assert err is not None and "долгого отдыха" in err

    short_rest_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=False)
    assert short_rest_changed is True
    runtime_after_short_rest = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime_after_short_rest.get("knowledge_past_life_uses_used") or 0) == 3

    long_rest_changed = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
    assert long_rest_changed is True
    runtime_after_long_rest = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime_after_long_rest.get("knowledge_past_life_uses_used") or 0) == 0
