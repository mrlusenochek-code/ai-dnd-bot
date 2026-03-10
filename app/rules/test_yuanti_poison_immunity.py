from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import _has_condition_immunity, _has_damage_immunity, _set_poisoned_condition


def _actor() -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "immunities": {"damage": ["poison"], "conditions": ["poisoned"]},
            "runtime": {},
        }
    )


def test_yuanti_poison_damage_is_immune() -> None:
    actor = _actor()
    assert _has_damage_immunity(actor, "poison") is True


def test_yuanti_poisoned_condition_is_not_applied() -> None:
    actor = _actor()
    assert _has_condition_immunity(actor, "poisoned") is True
    assert _set_poisoned_condition(actor, save_dc=12, rounds=10, source="test") is False
    runtime = (actor.race_features or {}).get("runtime") or {}
    conditions = runtime.get("conditions") or {}
    assert "poisoned" not in conditions
