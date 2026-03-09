from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def test_harengon_initiative_gets_proficiency_bonus(monkeypatch) -> None:
    ch = SimpleNamespace(
        level=5,
        stats={"dex": 50},
        race_features={"features": {"hare_trigger": {"type": "initiative_bonus", "bonus": "proficiency_bonus"}}},
    )

    monkeypatch.setattr("app.web.ws_handlers.roll_initiative", lambda _dex, rng=None: 11)
    total, bonus = ws_handlers._roll_initiative_with_racial_bonus(ch, rng=None)

    assert bonus == 3
    assert total == 14


def test_non_harengon_initiative_has_no_hare_trigger_bonus(monkeypatch) -> None:
    ch = SimpleNamespace(level=5, stats={"dex": 50}, race_features={"features": {}})

    monkeypatch.setattr("app.web.ws_handlers.roll_initiative", lambda _dex, rng=None: 11)
    total, bonus = ws_handlers._roll_initiative_with_racial_bonus(ch, rng=None)

    assert bonus == 0
    assert total == 11
