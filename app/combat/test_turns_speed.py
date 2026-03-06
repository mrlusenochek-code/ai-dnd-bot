from __future__ import annotations

from app.combat.state import Combatant, CombatState
from app.combat.turns import advance_turn_in_state


def test_advance_turn_resets_move_remaining_to_speed_ft() -> None:
    state = CombatState(
        active=True,
        round_no=1,
        turn_index=0,
        order=["pc_1", "enemy_1"],
        combatants={
            "pc_1": Combatant(
                key="pc_1",
                name="Hero",
                side="pc",
                hp_current=10,
                hp_max=10,
                ac=12,
                initiative=20,
                speed_ft=25,
                move_remaining=9,
            ),
            "enemy_1": Combatant(
                key="enemy_1",
                name="Goblin",
                side="enemy",
                hp_current=8,
                hp_max=8,
                ac=12,
                initiative=10,
                speed_ft=40,
                move_remaining=3,
            ),
        },
        started_at_iso=None,
    )

    advanced = advance_turn_in_state(state)

    assert advanced.turn_index == 1
    assert advanced.combatants["enemy_1"].move_remaining == 40
