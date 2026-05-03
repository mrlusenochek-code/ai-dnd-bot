from __future__ import annotations

from app.combat.live_actions import _actor_saving_throw_mod, handle_live_combat_action
from app.combat.state import Combatant, end_combat, start_combat


def _rogue_class_features(*, enabled: bool) -> dict:
    if not enabled:
        return {"features": [], "runtime": {}}
    return {
        "features": [
            {
                "key": "slippery_mind",
                "mechanics": {
                    "type": "saving_throw_proficiency",
                    "ability": "wis",
                    "source": "slippery_mind",
                },
            }
        ],
        "runtime": {},
    }


def test_combat_save_helper_adds_proficiency_only_for_wis() -> None:
    actor = Combatant(
        key="pc_1",
        name="Rogue",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=14,
        initiative=10,
        level=15,
        stats={"wis": 70, "dex": 70, "cha": 70},
        class_features=_rogue_class_features(enabled=True),
    )

    assert _actor_saving_throw_mod(actor, "wis") == 7
    assert _actor_saving_throw_mod(actor, "dex") == 2
    assert _actor_saving_throw_mod(actor, "cha") == 2


def test_combat_save_helper_does_not_change_non_rogue_actor() -> None:
    actor = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=14,
        initiative=10,
        level=15,
        stats={"wis": 70},
        class_features=_rogue_class_features(enabled=False),
    )

    assert _actor_saving_throw_mod(actor, "wis") == 2


def test_death_save_is_not_affected_by_slippery_mind(monkeypatch) -> None:
    session_id = "test_death_save_is_not_affected_by_slippery_mind"
    state = start_combat(session_id)
    state.combatants["pc_downed"] = Combatant(
        key="pc_downed",
        name="Downed Rogue",
        side="pc",
        hp_current=0,
        hp_max=24,
        ac=14,
        initiative=20,
        level=15,
        stats={"wis": 70},
        class_features=_rogue_class_features(enabled=True),
    )
    state.combatants["pc_ally"] = Combatant(
        key="pc_ally",
        name="Ally",
        side="pc",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=10,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=8,
        hp_max=8,
        ac=11,
        initiative=5,
    )
    state.order = ["pc_downed", "pc_ally", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode: (4, None, 4))

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        texts = [line.get("text", "") for line in (patch.get("lines") or []) if isinstance(line, dict)]
        assert any("Спасбросок смерти: d20(4)" in text for text in texts)
        assert not any("d20(7)" in text or "d20(10)" in text for text in texts)
    finally:
        end_combat(session_id)
