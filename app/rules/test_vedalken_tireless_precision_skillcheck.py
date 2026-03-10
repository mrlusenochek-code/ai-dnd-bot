from __future__ import annotations

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def _race_features() -> dict:
    return {
        "choices": {
            "tireless_precision": {
                "skill": "arcana",
                "tool": "thieves_tools",
            }
        },
        "bonuses": {
            "tireless_precision": {
                "die": "1d4",
                "skills": ["arcana"],
                "tools": ["thieves_tools"],
            }
        },
    }


def test_vedalken_tireless_precision_skillcheck_requires_proficiency() -> None:
    rf = _race_features()

    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="skill",
        key="arcana",
        proficient=True,
        rng=_FixedRng(3),
    )

    assert bonus == 3
    assert bonus_text == "1d4(3)"


def test_vedalken_tireless_precision_skillcheck_without_proficiency_gets_no_bonus() -> None:
    rf = _race_features()

    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="skill",
        key="arcana",
        proficient=False,
        rng=_FixedRng(3),
    )

    assert bonus == 0
    assert bonus_text == ""


def test_non_matching_skill_gets_no_tireless_precision_bonus() -> None:
    rf = _race_features()

    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="skill",
        key="history",
        proficient=True,
        rng=_FixedRng(4),
    )

    assert bonus == 0
    assert bonus_text == ""
