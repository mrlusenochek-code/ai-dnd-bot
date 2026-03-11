from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def test_shapechanger_assume_and_revert_respect_action_economy_in_combat() -> None:
    session_id = "test_shapechanger_assume_and_revert_respect_action_economy_in_combat"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        action_available=True,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    ch = SimpleNamespace(
        name="Changeling",
        race_features={
            "features": {"shapechanger": {"action": True, "equipment_unchanged": True}},
            "runtime": {},
        },
    )

    try:
        patch_1, err_1, changed_1 = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=True,
            persona="городской страж",
            voice="",
        )
        assert err_1 is None
        assert changed_1 is True
        assert patch_1 is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].action_available is False

        patch_blocked, err_blocked, changed_blocked = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=False,
        )
        assert patch_blocked is None
        assert changed_blocked is False
        assert err_blocked == "Действие недоступно: действие уже потрачено."

        state_now.combatants["pc_1"].action_available = True
        patch_2, err_2, changed_2 = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=False,
        )
        assert err_2 is None
        assert changed_2 is True
        assert patch_2 is not None
        assert state_now.combatants["pc_1"].action_available is False
    finally:
        end_combat(session_id)


def test_shapechanger_revert_without_active_form_does_not_spend_action() -> None:
    session_id = "test_shapechanger_revert_without_active_form_does_not_spend_action"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        action_available=True,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    ch = SimpleNamespace(
        name="Changeling",
        race_features={
            "features": {"shapechanger": {"action": True}},
            "runtime": {},
        },
    )

    try:
        patch, err, changed = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=False,
        )
        assert err is None
        assert changed is False
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].action_available is True
    finally:
        end_combat(session_id)
