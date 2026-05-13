from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import end_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def _fighter_second_wind_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(1) or []
    second_wind = next((item for item in features if str((item or {}).get("key") or "") == "second_wind"), None)
    assert isinstance(second_wind, dict)
    mechanics = second_wind.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_char_for_rest(*, hp: int, hp_max: int, sta: int, sta_max: int, hit_dice_remaining: int, hit_dice_max: int) -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        level=3,
        hp=hp,
        hp_max=hp_max,
        sta=sta,
        sta_max=sta_max,
        hit_die=10,
        hit_dice_remaining=hit_dice_remaining,
        hit_dice_max=hit_dice_max,
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "name_ru": "Второе дыхание",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {"second_wind_used": True},
        },
        race_features={"runtime": {}},
    )


def test_detect_long_rest_phrase_as_action() -> None:
    action = _detect_chat_combat_action("отдыхаю до утра")
    assert action == "rest_long"
    assert _detect_chat_combat_action("ложимся спать") == "rest_long"
    assert _detect_chat_combat_action("заночуем") == "rest_long"


def test_detect_short_rest_phrase_as_action() -> None:
    assert _detect_chat_combat_action("короткий отдых") == "rest_short"
    assert _detect_chat_combat_action("устроим привал") == "rest_short"
    assert _detect_chat_combat_action("отдохнём час") == "rest_short"
    assert _detect_chat_combat_action("переведем дух на привале") == "rest_short"


def test_long_rest_reset_reenables_innate_spell_with_long_rest_limit() -> None:
    ch = SimpleNamespace(
        level=3,
        race_features={
            "innate_spells": [
                {"ability": "con", "level": 1, "name": "burning_hands", "frequency": "1_per_long_rest", "min_level": 3}
            ],
            "runtime": {"relentless_endurance_used": True},
        },
    )

    first_display, first_err, first_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    second_display, second_err, second_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")

    assert first_err is None
    assert first_display == "burning_hands"
    assert first_changed is True
    assert second_display is None
    assert second_err is not None
    assert second_changed is False

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert "innate_spell_uses" not in runtime_after_reset
    assert "relentless_endurance_used" not in runtime_after_reset

    third_display, third_err, third_changed = ws_handlers._apply_innate_spell_usage(ch, "burning_hands")
    assert third_err is None
    assert third_display == "burning_hands"
    assert third_changed is True


def test_natural_language_short_rest_resets_second_wind_without_healing_hp() -> None:
    ch = _fighter_char_for_rest(hp=8, hp_max=20, sta=1, sta_max=7, hit_dice_remaining=2, hit_dice_max=3)

    result = ws_handlers._apply_personal_rest(ch, long_rest=False)

    assert int(ch.hp) == 8
    assert int(ch.sta) == 7
    assert int(ch.hit_dice_remaining) == 2
    assert result["class_reset"] is True
    runtime_after = (ch.class_features or {}).get("runtime") or {}
    assert "second_wind_used" not in runtime_after


def test_natural_language_long_rest_matches_full_long_rest_and_resets_second_wind() -> None:
    ch = _fighter_char_for_rest(hp=8, hp_max=20, sta=1, sta_max=7, hit_dice_remaining=1, hit_dice_max=4)

    result = ws_handlers._apply_personal_rest(ch, long_rest=True)

    assert int(ch.hp) == 20
    assert int(ch.sta) == 7
    assert int(ch.hit_dice_remaining) == 3
    assert result["old_hp"] == 8
    assert result["old_sta"] == 1
    assert result["hd_before"] == 1
    assert result["hd_after"] == 3
    assert result["class_reset"] is True
    runtime_after = (ch.class_features or {}).get("runtime") or {}
    assert "second_wind_used" not in runtime_after


def test_rest_is_blocked_in_active_combat_for_natural_language_short_and_long_rest() -> None:
    session_id = "test_rest_is_blocked_in_active_combat_for_natural_language_short_and_long_rest"
    start_combat(session_id)
    try:
        assert _detect_chat_combat_action("делаем привал") == "rest_short"
        assert _detect_chat_combat_action("долгий отдых") == "rest_long"
        assert ws_handlers._rest_unavailable_in_active_combat(session_id) == "Отдых недоступен во время боя."
    finally:
        end_combat(session_id)
