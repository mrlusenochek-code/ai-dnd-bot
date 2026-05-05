from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, start_combat


def _rogue_elusive_features() -> dict:
    return {
        "features": [
            {
                "key": "elusive",
                "mechanics": {
                    "type": "elusive",
                    "denies_attack_advantage": True,
                    "unless_condition": "incapacitated",
                },
            }
        ],
        "runtime": {},
    }


def _build_elusive_attack_state(session_id: str, *, dodge: bool = False, incapacitated: bool = False) -> None:
    state = start_combat(session_id)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=5,
        stats={"str": 60, "dex": 50},
        help_attack_advantage=True,
    )
    target_runtime = {"conditions": {"incapacitated": {"active": True}}} if incapacitated else {}
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Rogue",
        side="pc",
        hp_current=24,
        hp_max=24,
        ac=14,
        initiative=10,
        level=18,
        stats={"dex": 70},
        dodge_active=dodge,
        class_features=_rogue_elusive_features(),
        race_features={"runtime": target_runtime},
    )
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0


def test_elusive_cancels_attack_advantage_against_rogue_target(monkeypatch) -> None:
    session_id = "test_elusive_cancels_attack_advantage_against_rogue_target"
    _build_elusive_attack_state(session_id)
    modes: list[str] = []
    monkeypatch.setattr(
        "app.combat.live_actions.roll_check",
        lambda mode, **_kwargs: (modes.append(mode) or True) and (12, None, 12),
    )

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        assert modes and modes[0] == "normal"
    finally:
        end_combat(session_id)


def test_elusive_does_not_create_disadvantage_by_itself_but_keeps_existing_disadvantage(monkeypatch) -> None:
    session_id = "test_elusive_does_not_create_disadvantage_by_itself_but_keeps_existing_disadvantage"
    _build_elusive_attack_state(session_id, dodge=True)
    modes: list[str] = []
    monkeypatch.setattr(
        "app.combat.live_actions.roll_check",
        lambda mode, **_kwargs: (modes.append(mode) or True) and (12, 3, 3),
    )

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        assert modes and modes[0] == "disadvantage"
    finally:
        end_combat(session_id)


def test_elusive_does_not_cancel_advantage_while_target_is_incapacitated(monkeypatch) -> None:
    session_id = "test_elusive_does_not_cancel_advantage_while_target_is_incapacitated"
    _build_elusive_attack_state(session_id, incapacitated=True)
    modes: list[str] = []
    monkeypatch.setattr(
        "app.combat.live_actions.roll_check",
        lambda mode, **_kwargs: (modes.append(mode) or True) and (4, 17, 17),
    )

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        assert modes and modes[0] == "advantage"
    finally:
        end_combat(session_id)
