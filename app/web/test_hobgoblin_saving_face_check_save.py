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


def _build_character_from_actor(actor: Combatant) -> SimpleNamespace:
    return SimpleNamespace(
        race_features=dict(getattr(actor, "race_features", {}) or {}),
    )


def test_hobgoblin_saving_face_for_failed_check_and_save() -> None:
    session_id = "test_hobgoblin_saving_face_for_failed_check_and_save"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Hobgoblin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        reaction_available=True,
        race_features={
            "features": {
                "saving_face": {
                    "range_ft": 30,
                    "uses_max": 1,
                    "uses": "per_short_or_long_rest",
                    "bonus_formula": "min(allies_within_30ft, 5)",
                }
            },
            "runtime": {"saving_face_uses_used": 0},
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally 1",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=18,
    )
    state.combatants["pc_3"] = Combatant(
        key="pc_3",
        name="Ally 2",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=17,
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
    state.order = ["pc_1", "enemy_1", "pc_2", "pc_3"]
    state.turn_index = 0

    try:
        pc = state.combatants["pc_1"]
        ch = _build_character_from_actor(pc)

        check_bonus = ws_handlers._hobgoblin_mark_saving_face_pending(
            session_id=session_id,
            player_uid=1,
            ch=ch,
            kind="check",
            dc=15,
            total=13,
            details={"name": "athletics"},
        )
        assert check_bonus == 2

        check_patch, check_err = handle_live_combat_action("combat_saving_face", session_id)
        assert check_err is None
        assert check_patch is not None
        check_lines = _line_texts(check_patch)
        assert any("успех" in t.lower() for t in check_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        pc_now = state_now.combatants["pc_1"]
        runtime = (pc_now.race_features or {}).get("runtime") or {}
        assert int(runtime.get("saving_face_uses_used") or 0) == 1
        assert "saving_face_pending" not in runtime

        reset_changed = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False)
        assert reset_changed is True

        pc_now.reaction_available = True
        ch2 = _build_character_from_actor(pc_now)
        save_bonus = ws_handlers._hobgoblin_mark_saving_face_pending(
            session_id=session_id,
            player_uid=1,
            ch=ch2,
            kind="save",
            dc=14,
            total=12,
            details={"ability": "wis"},
        )
        assert save_bonus == 2

        save_patch, save_err = handle_live_combat_action("combat_saving_face", session_id)
        assert save_err is None
        assert save_patch is not None
        save_lines = _line_texts(save_patch)
        assert any("успех" in t.lower() for t in save_lines)
    finally:
        end_combat(session_id)
