from __future__ import annotations

from types import SimpleNamespace

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


def test_kender_fearless_advantage_and_reaction_auto_success_with_long_rest_reset() -> None:
    session_id = "test_kender_fearless_advantage_and_reaction_auto_success_with_long_rest_reset"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Kender",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
        race_features={
            "features": {
                "fearless_vs_frightened": {
                    "advantage": True,
                    "auto_success_max": 1,
                    "recharge": "per_long_rest",
                }
            },
            "saves": {"advantage_conditions": ["frightened"]},
            "runtime": {"fearless_auto_success_used": 0},
        },
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

    try:
        mode = ws_handlers._effective_save_mode(
            "normal",
            state.combatants["pc_1"].race_features,
            "wis",
            vs_tag="frightened",
        )
        assert mode == "advantage"

        ch = SimpleNamespace(race_features=dict(state.combatants["pc_1"].race_features or {}))
        marked = ws_handlers._kender_mark_fearless_pending(
            session_id=session_id,
            player_uid=1,
            ch=ch,
            dc=15,
            total=11,
            ability="wis",
            vs_tag="frightened",
        )
        assert marked is True

        patch, err = handle_live_combat_action("combat_fearless", session_id)
        assert err is None
        assert patch is not None
        lines = _line_texts(patch)
        assert any("становится успешным" in t.lower() for t in lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc = state_now.combatants["pc_1"]
        assert pc.reaction_available is False
        runtime = (pc.race_features or {}).get("runtime") or {}
        assert int(runtime.get("fearless_auto_success_used") or 0) == 1
        assert "fearless_pending_failed_frightened_save" not in runtime

        patch_2, err_2 = handle_live_combat_action("combat_fearless", session_id)
        assert patch_2 is None
        assert err_2 is not None
        assert ("использовано" in err_2.lower()) or ("нет проваленного" in err_2.lower())

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=True)
        assert reset_changed is True
        runtime_after = ((pc.race_features or {}).get("runtime") or {})
        assert "fearless_auto_success_used" not in runtime_after
        assert "fearless_pending_failed_frightened_save" not in runtime_after
    finally:
        end_combat(session_id)
