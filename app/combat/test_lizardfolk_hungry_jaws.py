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


def test_lizardfolk_hungry_jaws_bonus_action_temp_hp_and_rest_reset(monkeypatch) -> None:
    session_id = "test_lizardfolk_hungry_jaws_bonus_action_temp_hp_and_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Lizardfolk",
        side="pc",
        hp_current=20,
        hp_max=20,
        temp_hp=0,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 60, "dex": 50, "con": 60, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "hungry_jaws": {
                    "activation": "bonus_action",
                    "temp_hp_formula": "max(con_mod,1)",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {},
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=10,
        initiative=10,
        stats={"str": 50, "dex": 50, "con": 50, "wis": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([12, 4, 12, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_hungry_jaws", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("голодная пасть" in t.lower() for t in texts)
        assert any("временные хиты" in t.lower() for t in texts)

        st = get_combat(session_id)
        assert st is not None
        actor = st.combatants["pc_1"]
        assert actor.bonus_action_available is False
        assert max(0, int(getattr(actor, "temp_hp", 0) or 0)) >= 1
        runtime = ((actor.race_features or {}).get("runtime") or {})
        assert int(runtime.get("hungry_jaws_uses_used") or 0) == 1

        patch_again, err_again = handle_live_combat_action("combat_hungry_jaws", session_id)
        assert patch_again is None
        assert err_again is not None
        assert "использована" in err_again.lower() or "использован" in err_again.lower()

        assert ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False) is True
        st = get_combat(session_id)
        assert st is not None
        runtime_reset = ((st.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert "hungry_jaws_uses_used" not in runtime_reset

        st.combatants["pc_1"].bonus_action_available = True
        patch_after_rest, err_after_rest = handle_live_combat_action("combat_hungry_jaws", session_id)
        assert err_after_rest is None
        assert patch_after_rest is not None
    finally:
        end_combat(session_id)
