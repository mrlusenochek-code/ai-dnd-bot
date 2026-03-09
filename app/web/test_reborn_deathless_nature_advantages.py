from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.web import ws_handlers


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def test_reborn_effective_save_mode_advantage_for_disease_and_poisoned() -> None:
    race_features = {
        "saves": {
            "advantage_conditions": ["disease", "poisoned", "death_saves"],
        }
    }

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="disease") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="болезнь") == "advantage"
    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poisoned") == "advantage"


def test_reborn_death_save_has_advantage(monkeypatch) -> None:
    session_id = "test_reborn_death_save_has_advantage"
    state = start_combat(session_id)
    state.combatants["pc_reborn"] = Combatant(
        key="pc_reborn",
        name="Reborn",
        side="pc",
        hp_current=0,
        hp_max=12,
        ac=13,
        initiative=20,
        level=3,
        race_features={
            "saves": {"advantage_conditions": ["death_saves"]},
            "features": {
                "deathless_nature": {
                    "advantage_on_saves": ["disease", "poisoned", "death_saves"],
                    "long_rest_hours": 4,
                    "remain_conscious": True,
                }
            },
        },
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
    state.order = ["pc_reborn", "pc_ally", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr(
        "app.combat.live_actions.roll_check",
        lambda mode: (3, 17, 17) if mode == "advantage" else (3, None, 3),
    )

    try:
        patch, err = handle_live_combat_action("combat_end_turn", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Бессмертная природа" in t for t in texts)
        assert any("Результат: успех." in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert int(state_now.combatants["pc_reborn"].death_successes or 0) == 1
    finally:
        end_combat(session_id)
