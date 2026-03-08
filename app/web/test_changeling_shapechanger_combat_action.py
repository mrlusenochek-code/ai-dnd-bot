from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def test_shapechanger_in_combat_requires_turn_and_spends_action() -> None:
    session_id = "test_shapechanger_in_combat_requires_turn_and_spends_action"
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
            active=True,
            persona="городской страж",
            voice="",
        )
        assert err is None
        assert changed is True
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].action_available is False

        state_now.combatants["pc_1"].action_available = True
        state_now.turn_index = 1
        patch_2, err_2, changed_2 = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=False,
        )
        assert patch_2 is None
        assert changed_2 is False
        assert err_2 is not None
        assert "Сейчас ходит" in err_2
    finally:
        end_combat(session_id)
