from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.rules.class_feature_runtime import mark_failed_save_for_indomitable
from app.web.ws_class_features import apply_combat_class_feature_action
from app.web.ws_gameplay import _detect_chat_combat_action


class _FixedRng:
    def __init__(self, *values: int):
        self._values = list(values)

    def randint(self, _start: int, _end: int) -> int:
        if not self._values:
            raise AssertionError("No more fixed RNG values")
        return self._values.pop(0)


def _fighter_indomitable_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(9) or []
    indomitable = next((item for item in features if str((item or {}).get("key") or "") == "indomitable_1"), None)
    assert isinstance(indomitable, dict)
    mechanics = indomitable.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_character() -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        class_features={
            "features": [
                {
                    "key": "indomitable_1",
                    "name_ru": "Несгибаемый",
                    "mechanics": _fighter_indomitable_mechanics(),
                }
            ],
            "runtime": {},
        },
    )


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def test_detect_indomitable_phrases_as_combat_action() -> None:
    assert _detect_chat_combat_action("несгибаемый") == "combat_indomitable"
    assert _detect_chat_combat_action("использую несгибаемый") == "combat_indomitable"
    assert _detect_chat_combat_action("indomitable") == "combat_indomitable"


def test_failed_save_can_create_indomitable_pending_runtime() -> None:
    ch = _fighter_character()
    changed = mark_failed_save_for_indomitable(
        ch,
        ability="wis",
        vs_tag="frightened",
        dc=15,
        total=12,
        mode="normal",
        mod=2,
        bonus_total=1,
        bonus_texts=["1d4 (Создан для успеха: 1)"],
    )
    assert changed is True
    runtime = (ch.class_features or {}).get("runtime") or {}
    pending = runtime.get("indomitable_pending_failed_save") or {}
    assert pending.get("ability") == "wis"
    assert pending.get("dc") == 15
    assert pending.get("old_total") == 12


def test_indomitable_router_requires_active_combat() -> None:
    ch = _fighter_character()
    mark_failed_save_for_indomitable(
        ch,
        ability="wis",
        vs_tag="frightened",
        dc=15,
        total=12,
        mode="normal",
        mod=2,
    )
    patch, err, changed = apply_combat_class_feature_action("combat_indomitable", "missing_session", "pc_1", ch, rng=_FixedRng(18))
    assert patch is None
    assert err == "Несгибаемый сейчас доступен только в бою."
    assert changed is False


def test_indomitable_in_combat_rerolls_pending_without_turn_requirement() -> None:
    session_id = "test_indomitable_in_combat_rerolls_pending_without_turn_requirement"
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
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=20,
    )
    state.order = ["enemy_1", "pc_1"]
    state.turn_index = 0

    try:
        mark_failed_save_for_indomitable(
            ch,
            ability="wis",
            vs_tag="frightened",
            dc=15,
            total=12,
            mode="normal",
            mod=2,
        )
        patch, err, changed = apply_combat_class_feature_action(
            "combat_indomitable",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(17),
        )
        assert err is None
        assert patch is not None
        assert changed is True
        lines = _line_texts(patch)
        assert any("Несгибаемый" in text for text in lines)
        assert any("SUCCESS" in text for text in lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.action_available is False
        assert actor.bonus_action_available is False

        runtime = (ch.class_features or {}).get("runtime") or {}
        assert int(runtime.get("indomitable_used") or 0) == 1
        assert "indomitable_pending_failed_save" not in runtime

        patch_repeat, err_repeat, changed_repeat = apply_combat_class_feature_action(
            "combat_indomitable",
            session_id,
            "pc_1",
            ch,
            rng=_FixedRng(19),
        )
        assert patch_repeat is None
        assert err_repeat == "Нет проваленного спасброска для «Несгибаемого»."
        assert changed_repeat is False
    finally:
        end_combat(session_id)
