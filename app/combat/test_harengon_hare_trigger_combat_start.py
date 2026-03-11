from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_harengon_hare_trigger_initiative_details_include_pb_bonus(monkeypatch) -> None:
    ch = SimpleNamespace(
        level=5,
        stats={"dex": 50},
        race_features={"features": {"hare_trigger": {"type": "initiative_bonus", "bonus": "proficiency_bonus"}}},
    )

    monkeypatch.setattr("app.web.ws_handlers.roll_initiative", lambda _dex, rng=None: 11)
    total, base, dex_mod, hare_bonus = ws_handlers._roll_initiative_details(ch, rng=None)

    assert base == 11
    assert dex_mod == 0
    assert hare_bonus == 3
    assert total == 14


def test_initiative_log_line_shows_hare_trigger_breakdown() -> None:
    line = ws_handlers._format_initiative_roll_line(
        "Harengon Scout",
        total=16,
        base=14,
        dex_mod=0,
        hare_bonus=2,
    )

    assert line == "Harengon Scout: d20(14) + ЛОВ +0 + Заячье сердце +2 = 16"
