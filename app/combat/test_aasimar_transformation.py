from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import handle_live_combat_action
from app.combat.resolution import AttackResolution
from app.combat.state import Combatant, add_enemy, end_combat, get_combat, start_combat, upsert_pc
from app.web import ws_handlers


def _patch_line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(str(item.get("text")))
    return out


def _aasimar_char(*, kind: str, level: int = 3):
    features: dict[str, object] = {
        "kind": kind,
        "min_level": 3,
        "duration": "1_minute",
        "uses": "per_long_rest",
        "uses_max": 1,
    }
    if kind == "protector":
        features["fly_speed_ft"] = 30
        features["bonus_damage"] = {"type": "radiant", "frequency": "once_per_turn"}
    elif kind == "fallen":
        features["fear_on_transform"] = {"radius_ft": 10, "save_ability": "cha", "dc_formula": "8 + proficiency_bonus + cha_mod"}
        features["bonus_damage"] = {"type": "necrotic", "frequency": "once_per_turn"}
    elif kind == "scourge":
        features["self_damage"] = {"type": "radiant", "frequency": "each_turn"}
        features["end_of_turn_aura_damage"] = {"type": "radiant", "radius_ft": 10, "amount": "ceil(level/2)"}
        features["light_emission"] = {"bright_ft": 10, "dim_ft": 10}
    return SimpleNamespace(
        name=f"Aasimar {kind}",
        level=level,
        hp=20,
        hp_max=20,
        race_features={"features": {"aasimar_transformation": features}},
    )


def test_protector_transformation_activation_spends_action_and_does_not_reset_on_short_rest() -> None:
    session_id = "test_protector_transformation_activation_spends_action_and_does_not_reset_on_short_rest"
    ch = _aasimar_char(kind="protector", level=3)
    try:
        start_combat(session_id, reason="test")
        upsert_pc(
            session_id,
            pc_key="pc_1",
            name="Protector",
            hp=20,
            hp_max=20,
            ac=12,
            initiative=10,
            level=3,
            race_features=ch.race_features,
        )
        add_enemy(session_id, name="Bandit", hp=10, ac=12, enemy_id="enemy_1")
        state = get_combat(session_id)
        assert state is not None
        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0

        patch, err, changed = ws_handlers._apply_aasimar_transformation_in_combat(session_id, "pc_1", ch)
        assert err is None
        assert patch is not None
        assert changed is True
        texts = _patch_line_texts(patch)
        assert any("Небесное преобразование (Защитник)" in text for text in texts)

        runtime = (ch.race_features or {}).get("runtime") or {}
        transform = runtime.get("aasimar_transformation") or {}
        assert runtime.get("aasimar_transform_used") is True
        assert transform.get("active") is True
        assert transform.get("kind") == "protector"
        assert int(transform.get("rounds_left") or 0) == 10
        assert int(runtime.get("fly_speed_ft") or 0) == 30
        assert state.combatants["pc_1"].action_available is False

        reset_short = ws_handlers._reset_racial_rest_uses(ch, long_rest=False)
        assert reset_short is True
        runtime_after_short = (ch.race_features or {}).get("runtime") or {}
        assert runtime_after_short.get("aasimar_transform_used") is True
        assert "aasimar_transformation" not in runtime_after_short
        assert "fly_speed_ft" not in runtime_after_short

        state.combatants["pc_1"].race_features = ch.race_features
        reset_short_combat = ws_handlers._reset_combatant_racial_rest_uses(session_id, "pc_1", long_rest=False)
        assert reset_short_combat is False
        combat_runtime_after_short = (state.combatants["pc_1"].race_features or {}).get("runtime") or {}
        assert combat_runtime_after_short.get("aasimar_transform_used") is True

        reset_long = ws_handlers._reset_racial_rest_uses(ch, long_rest=True)
        assert reset_long is True
        runtime_after_long = (ch.race_features or {}).get("runtime") or {}
        assert "aasimar_transform_used" not in runtime_after_long
    finally:
        end_combat(session_id)


def test_fallen_transformation_bonus_damage_once_per_turn(monkeypatch) -> None:
    session_id = "test_fallen_transformation_bonus_damage_once_per_turn"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fallen Aasimar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=3,
        race_features={
            "features": {
                "aasimar_transformation": {
                    "kind": "fallen",
                    "min_level": 3,
                    "duration": "1_minute",
                    "uses": "per_long_rest",
                    "uses_max": 1,
                    "fear_on_transform": {"radius_ft": 10, "save_ability": "cha", "dc_formula": "8 + proficiency_bonus + cha_mod"},
                    "bonus_damage": {"type": "necrotic", "frequency": "once_per_turn"},
                }
            },
            "runtime": {
                "aasimar_transform_used": True,
                "aasimar_transformation": {"active": True, "kind": "fallen", "rounds_left": 10},
            },
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=100,
        hp_max=100,
        ac=10,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    def _always_hit(**kwargs):
        return AttackResolution(
            d20_roll=15,
            attack_bonus=int(kwargs.get("attack_bonus") or 0),
            target_ac=int(kwargs.get("target_ac") or 10),
            total_to_hit=99,
            is_hit=True,
            is_crit=False,
            damage_roll=4,
            damage_bonus=0,
            total_damage=4,
        )

    monkeypatch.setattr("app.combat.live_actions.resolve_attack_roll", _always_hit)

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None and patch_1 is not None
        texts_1 = _patch_line_texts(patch_1)
        assert any("Доп. урон трансформации: +3 necrotic (1/ход)." in text for text in texts_1)
        assert any("Урон: 4 + 0 = 7" in text for text in texts_1)

        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True

        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None and patch_2 is not None
        texts_2 = _patch_line_texts(patch_2)
        assert not any("Доп. урон трансформации" in text for text in texts_2)
        assert any("Урон: 4 + 0 = 4" in text for text in texts_2)
    finally:
        end_combat(session_id)


def test_scourge_transformation_activation_sets_runtime_metadata() -> None:
    ch = _aasimar_char(kind="scourge", level=3)

    runtime, err, changed = ws_handlers._apply_aasimar_transformation_usage(ch)
    assert err is None
    assert changed is True
    assert isinstance(runtime, dict)
    assert runtime.get("active") is True
    assert runtime.get("kind") == "scourge"
    assert int(runtime.get("rounds_left") or 0) == 10

    rf_runtime = (ch.race_features or {}).get("runtime") or {}
    assert rf_runtime.get("aasimar_transform_used") is True
