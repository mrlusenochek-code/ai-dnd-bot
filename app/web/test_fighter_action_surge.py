from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web import ws_handlers
from app.web.ws_class_features import apply_combat_class_feature_action
from app.web.ws_gameplay import _detect_chat_combat_action


def _fighter_action_surge_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(2) or []
    action_surge = next((item for item in features if str((item or {}).get("key") or "") == "action_surge"), None)
    assert isinstance(action_surge, dict)
    mechanics = action_surge.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_character() -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        hp=20,
        hp_max=20,
        sta=2,
        sta_max=5,
        hit_die=10,
        hit_dice_remaining=2,
        hit_dice_max=3,
        class_features={
            "features": [
                {
                    "key": "action_surge",
                    "name_ru": "Всплеск действий",
                    "mechanics": _fighter_action_surge_mechanics(),
                }
            ],
            "runtime": {},
        },
        race_features={"runtime": {}},
    )


def test_detect_action_surge_phrases_as_combat_action() -> None:
    assert _detect_chat_combat_action("всплеск действий") == "combat_action_surge"
    assert _detect_chat_combat_action("всплеск действия") == "combat_action_surge"
    assert _detect_chat_combat_action("использую всплеск действий") == "combat_action_surge"
    assert _detect_chat_combat_action("делаю ещё одно действие") == "combat_action_surge"
    assert _detect_chat_combat_action("делаю еще одно действие") == "combat_action_surge"
    assert _detect_chat_combat_action("действую ещё раз") == "combat_action_surge"
    assert _detect_chat_combat_action("действую еще раз") == "combat_action_surge"
    assert _detect_chat_combat_action("хочу действовать ещё раз") == "combat_action_surge"
    assert _detect_chat_combat_action("хочу действовать еще раз") == "combat_action_surge"
    assert _detect_chat_combat_action("собираюсь и действую ещё раз") == "combat_action_surge"
    assert _detect_chat_combat_action("собираюсь и действую еще раз") == "combat_action_surge"
    assert _detect_chat_combat_action("выкладываюсь на максимум") == "combat_action_surge"
    assert _detect_chat_combat_action("рывок действий") == "combat_action_surge"
    assert _detect_chat_combat_action("action surge") == "combat_action_surge"


def test_action_surge_router_requires_active_combat() -> None:
    ch = _fighter_character()
    patch, err, changed = apply_combat_class_feature_action("combat_action_surge", "missing_session", "pc_1", ch)
    assert patch is None
    assert err == "Combat is not active"
    assert changed is False


def test_action_surge_router_requires_feature_on_character() -> None:
    session_id = "test_action_surge_router_requires_feature_on_character"
    ch = SimpleNamespace(name="Commoner", class_features={"features": [], "runtime": {}})
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Commoner",
        side="pc",
        hp_current=8,
        hp_max=8,
        ac=10,
        initiative=15,
        action_available=False,
        bonus_action_available=True,
        reaction_available=True,
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    try:
        patch, err, changed = apply_combat_class_feature_action("combat_action_surge", session_id, "pc_1", ch)
        assert patch is None
        assert err == "Всплеск действий недоступен вашему классу."
        assert changed is False
    finally:
        end_combat(session_id)


def test_action_surge_router_requires_own_turn_and_grants_action_once() -> None:
    session_id = "test_action_surge_router_requires_own_turn_and_grants_action_once"
    ch = _fighter_character()
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=16,
        initiative=15,
        action_available=False,
        bonus_action_available=True,
        reaction_available=True,
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
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert patch_wrong is None
        assert err_wrong is not None
        assert "Дождись своего хода" in err_wrong
        assert changed_wrong is False

        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0
        patch_ok, err_ok, changed_ok = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert err_ok is None
        assert patch_ok is not None
        assert changed_ok is True

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.action_available is True
        assert actor.bonus_action_available is True
        assert actor.reaction_available is True
        lines = patch_ok.get("lines") if isinstance(patch_ok, dict) else []
        first_text = ""
        if isinstance(lines, list) and lines and isinstance(lines[0], dict):
            first_text = str(lines[0].get("text") or "")
        assert "Всплеск действий" in first_text

        patch_repeat, err_repeat, changed_repeat = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert patch_repeat is None
        assert err_repeat is not None
        assert "короткого или долгого отдыха" in err_repeat
        assert changed_repeat is False
    finally:
        end_combat(session_id)


def test_action_surge_router_does_not_restore_bonus_action_or_reaction() -> None:
    session_id = "test_action_surge_router_does_not_restore_bonus_action_or_reaction"
    ch = _fighter_character()
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=16,
        initiative=15,
        action_available=False,
        bonus_action_available=False,
        reaction_available=False,
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    try:
        patch, err, changed = apply_combat_class_feature_action("combat_action_surge", session_id, "pc_1", ch)
        assert err is None
        assert patch is not None
        assert changed is True

        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert actor.action_available is True
        assert actor.bonus_action_available is False
        assert actor.reaction_available is False
    finally:
        end_combat(session_id)


def test_action_surge_router_blocks_when_actor_has_zero_hp_without_spending_use() -> None:
    session_id = "test_action_surge_router_blocks_when_actor_has_zero_hp_without_spending_use"
    ch = _fighter_character()
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=0,
        hp_max=20,
        ac=16,
        initiative=15,
        action_available=False,
        bonus_action_available=True,
        reaction_available=True,
    )
    state.order = ["pc_1"]
    state.turn_index = 0

    try:
        patch, err, changed = apply_combat_class_feature_action("combat_action_surge", session_id, "pc_1", ch)
        assert patch is None
        assert err == "Всплеск действий недоступен: персонаж не может действовать."
        assert changed is False

        actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
        assert actor.action_available is False
        assert actor.bonus_action_available is True
        assert actor.reaction_available is True
        runtime_after = (ch.class_features or {}).get("runtime") or {}
        assert "action_surge_used" not in runtime_after
    finally:
        end_combat(session_id)


def test_action_surge_router_blocks_when_actor_is_defeated_or_dead() -> None:
    for attr_name in ("is_dead", "defeated", "is_defeated"):
        session_id = f"test_action_surge_router_blocks_{attr_name}"
        ch = _fighter_character()
        state = start_combat(session_id)
        state.combatants["pc_1"] = Combatant(
            key="pc_1",
            name="Fighter",
            side="pc",
            hp_current=20,
            hp_max=20,
            ac=16,
            initiative=15,
            action_available=False,
            bonus_action_available=True,
            reaction_available=False,
        )
        setattr(state.combatants["pc_1"], attr_name, True)
        state.order = ["pc_1"]
        state.turn_index = 0

        try:
            patch, err, changed = apply_combat_class_feature_action("combat_action_surge", session_id, "pc_1", ch)
            assert patch is None
            assert err == "Всплеск действий недоступен: персонаж не может действовать."
            assert changed is False

            actor = get_combat(session_id).combatants["pc_1"]  # type: ignore[union-attr]
            assert actor.action_available is False
            assert actor.bonus_action_available is True
            assert actor.reaction_available is False
            runtime_after = (ch.class_features or {}).get("runtime") or {}
            assert "action_surge_used" not in runtime_after
        finally:
            end_combat(session_id)


def test_natural_language_short_rest_resets_action_surge_usage() -> None:
    ch = _fighter_character()
    assert _detect_chat_combat_action("делаем привал") == "rest_short"
    ch.class_features["runtime"] = {"action_surge_used": 1}

    result = ws_handlers._apply_personal_rest(ch, long_rest=False)

    assert result["class_reset"] is True
    runtime_after = (ch.class_features or {}).get("runtime") or {}
    assert "action_surge_used" not in runtime_after


def test_natural_language_long_rest_resets_action_surge_usage() -> None:
    ch = _fighter_character()
    assert _detect_chat_combat_action("долгий отдых") == "rest_long"
    ch.class_features["runtime"] = {"action_surge_used": 1}

    result = ws_handlers._apply_personal_rest(ch, long_rest=True)

    assert result["class_reset"] is True
    runtime_after = (ch.class_features or {}).get("runtime") or {}
    assert "action_surge_used" not in runtime_after
