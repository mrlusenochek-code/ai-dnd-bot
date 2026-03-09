from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def test_kobold_pack_tactics_advantage_when_ally_alive() -> None:
    session_id = "test_kobold_pack_tactics_advantage_when_ally_alive"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kobold",
        side="pc",
        hp_current=18,
        hp_max=18,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        stats={"str": 40, "dex": 60, "con": 50},
        race_features={"features": {"pack_tactics": {"enabled": True}}},
        inventory=[{"id": "w1", "def": "dagger", "name": "Кинжал", "qty": 1}],
        equip={"main_hand": "w1"},
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally",
        side="pc",
        hp_current=18,
        hp_max=18,
        ac=12,
        initiative=15,
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
    state.order = ["pc_1", "enemy_1", "pc_2"]
    state.turn_index = 0

    import app.combat.live_actions as live_actions

    seq = iter([3, 18, 4, 11, 4])
    old_randint = live_actions.random.randint
    live_actions.random.randint = lambda _a, _b: next(seq)
    try:
        patch_adv, err_adv = handle_live_combat_action("combat_attack", session_id)
        assert err_adv is None
        assert patch_adv is not None
        assert any("d20(3,18) -> 18" in t for t in _line_texts(patch_adv))

        st = get_combat(session_id)
        assert st is not None
        st.turn_index = 0
        st.combatants["pc_1"].action_available = True
        st.combatants["pc_2"].hp_current = 0
        st.combatants["pc_2"].is_dead = True

        patch_no_adv, err_no_adv = handle_live_combat_action("combat_attack", session_id)
        assert err_no_adv is None
        assert patch_no_adv is not None
        assert any("d20(11)" in t for t in _line_texts(patch_no_adv))
    finally:
        live_actions.random.randint = old_randint
        end_combat(session_id)
