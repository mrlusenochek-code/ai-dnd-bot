from __future__ import annotations

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def _race_features(skill: str, tool: str) -> dict:
    return {
        "choices": {
            "tireless_precision": {
                "skill": skill,
                "tool": tool,
            }
        },
        "bonuses": {
            "tireless_precision": {
                "die": "1d4",
                "skills": [skill],
                "tools": [tool],
            }
        },
    }


def test_tireless_precision_bonus_applies_to_selected_skill_check() -> None:
    rf = _race_features("arcana", "thieves_tools")
    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="skill",
        key="arcana",
        rng=_FixedRng(3),
    )
    base_total = 12
    total = base_total + bonus

    assert bonus == 3
    assert bonus_text == "1d4(3)"
    assert total == 15


def test_tireless_precision_bonus_applies_to_selected_toolcheck() -> None:
    rf = _race_features("arcana", "thieves_tools")
    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="tool",
        key="thieves_tools",
        rng=_FixedRng(4),
    )
    base_total = 11
    total = base_total + bonus

    assert bonus == 4
    assert bonus_text == "1d4(4)"
    assert total == 15
