from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def _race_features(tool: str | None) -> dict:
    return {
        "choices": {
            "tireless_precision": {
                "skill": "arcana",
                "tool": tool or "",
            }
        },
        "bonuses": {
            "tireless_precision": {
                "die": "1d4",
                "skills": ["arcana"],
                "tools": ([tool] if tool else []),
            }
        },
    }


def test_toolcheck_tireless_precision_applies_only_to_matching_tool() -> None:
    rf = _race_features("thieves_tools")

    matching_bonus, matching_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="tool",
        key="thieves_tools",
        rng=_FixedRng(3),
    )
    non_matching_bonus, non_matching_text = ws_handlers._tireless_precision_bonus_for_check(
        rf,
        kind="tool",
        key="alchemists_supplies",
        rng=_FixedRng(3),
    )

    assert matching_bonus == 3
    assert matching_text == "1d4(3)"
    assert non_matching_bonus == 0
    assert non_matching_text == ""


def test_toolcheck_tireless_precision_absent_character_gets_no_bonus() -> None:
    bonus, bonus_text = ws_handlers._tireless_precision_bonus_for_check(
        SimpleNamespace(),
        kind="tool",
        key="thieves_tools",
        rng=_FixedRng(4),
    )
    assert bonus == 0
    assert bonus_text == ""


def test_toolcheck_log_includes_tireless_precision_bonus() -> None:
    log = ws_handlers._format_toolcheck_log(
        tool_name_ru="Воровские инструменты",
        mode="advantage",
        roll_a=7,
        roll_b=15,
        roll=15,
        mod=0,
        tp_bonus=3,
        tp_bonus_text="1d4(3)",
        extra_bonus_texts=[],
        total=18,
        dc=15,
    )

    assert "[TOOL] Проверка инструмента: Воровские инструменты" in log
    assert "Бросок: adv d20(7, 15) -> 15" in log
    assert "Tireless Precision: +1d4(3)" in log
    assert "Итого: 18" in log
    assert "DC 15 -> успех" in log
