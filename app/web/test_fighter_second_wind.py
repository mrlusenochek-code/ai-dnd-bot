from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web.ws_class_features import apply_combat_class_feature_action
from app.web.ws_gameplay import _detect_chat_combat_action


class _FixedRng:
    def __init__(self, *values: int):
        self._values = list(values)

    def randint(self, _start: int, _end: int) -> int:
        if not self._values:
            raise AssertionError("No more fixed RNG values")
        return self._values.pop(0)


def _fighter_second_wind_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(1) or []
    second_wind = next((item for item in features if str((item or {}).get("key") or "") == "second_wind"), None)
    assert isinstance(second_wind, dict)
    mechanics = second_wind.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_character(*, hp: int = 6, hp_max: int = 20, level: int = 3) -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        level=level,
        hp=hp,
        hp_max=hp_max,
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "name_ru": "Второе дыхание",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {},
        },
    )


def test_detect_second_wind_phrases_as_combat_action() -> None:
    assert _detect_chat_combat_action("использую второе дыхание") == "combat_second_wind"
    assert _detect_chat_combat_action("второе дыхание") == "combat_second_wind"
    assert _detect_chat_combat_action("перевожу дух") == "combat_second_wind"
    assert _detect_chat_combat_action("собираюсь с силами") == "combat_second_wind"
    assert _detect_chat_combat_action("отдышусь") == "combat_second_wind"
    assert _detect_chat_combat_action("second wind") == "combat_second_wind"


def test_second_wind_in_combat_requires_turn_spends_bonus_action_and_syncs_hp() -> None:
    session_id = "test_second_wind_in_combat_requires_turn_spends_bonus_action_and_syncs_hp"
    ch = _fighter_character(hp=6, hp_max=20, level=3)
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=6,
        hp_max=20,
        ac=16,
        initiative=15,
        bonus_action_available=True,
        level=3,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=10,
    )

    try:
        state.order = ["enemy_1", "pc_1"]
        state.turn_index = 0
        patch_wrong, err_wrong, changed_wrong = apply_combat_class_feature_action(
            "combat_second_wind",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(5),
        )
        assert patch_wrong is None
        assert err_wrong is not None
        assert "Дождись своего хода" in err_wrong
        assert changed_wrong is False

        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0
        patch_ok, err_ok, changed_ok = apply_combat_class_feature_action(
            "combat_second_wind",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(5),
        )
        assert err_ok is None
        assert patch_ok is not None
        assert changed_ok is True
        assert ch.hp == 14

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.hp_current == 14
        assert actor.bonus_action_available is False
        runtime = (ch.class_features or {}).get("runtime") or {}
        assert runtime.get("second_wind_used") is True

        actor.bonus_action_available = True
        patch_repeat, err_repeat, changed_repeat = apply_combat_class_feature_action(
            "combat_second_wind",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(7),
        )
        assert patch_repeat is None
        assert err_repeat is not None
        assert "короткого или долгого отдыха" in err_repeat
        assert changed_repeat is False
    finally:
        end_combat(session_id)


def test_second_wind_blocks_when_actor_cannot_act_at_zero_hp() -> None:
    session_id = "test_second_wind_blocks_when_actor_cannot_act_at_zero_hp"
    ch = _fighter_character(hp=0, hp_max=20, level=3)
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=0,
        hp_max=20,
        ac=16,
        initiative=15,
        bonus_action_available=True,
        level=3,
        is_dead=False,
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    try:
        patch, err, changed = apply_combat_class_feature_action(
            "combat_second_wind",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(5),
        )
        assert patch is None
        assert err == "Второе дыхание недоступно: персонаж не может действовать."
        assert changed is False
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert actor.bonus_action_available is True
        assert ((ch.class_features or {}).get("runtime") or {}).get("second_wind_used") is not True
    finally:
        end_combat(session_id)


def test_second_wind_at_full_hp_spends_resource_and_clamps_heal() -> None:
    session_id = "test_second_wind_at_full_hp_spends_resource_and_clamps_heal"
    ch = _fighter_character(hp=20, hp_max=20, level=3)
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=16,
        initiative=15,
        bonus_action_available=True,
        level=3,
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    try:
        patch, err, changed = apply_combat_class_feature_action(
            "combat_second_wind",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(10),
        )
        assert err is None
        assert patch is not None
        assert changed is True
        assert ch.hp == 20
        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert actor.hp_current == 20
        assert actor.bonus_action_available is False
        assert ((ch.class_features or {}).get("runtime") or {}).get("second_wind_used") is True
        lines = patch.get("lines") or []
        assert isinstance(lines, list)
        assert any("+0 HP" in str((item or {}).get("text") or "") for item in lines if isinstance(item, dict))
    finally:
        end_combat(session_id)
