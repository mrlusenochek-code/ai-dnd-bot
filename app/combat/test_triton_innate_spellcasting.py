from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _triton_rf(level: int) -> dict:
    return {
        "race_key": "triton",
        "innate_spells": [
            {"ability": "cha", "level": 0, "name": "create_or_destroy_water", "frequency": "at_will", "min_level": 1},
            {"ability": "cha", "level": 2, "name": "gust_of_wind", "frequency": "1_per_long_rest", "min_level": 3},
            {"ability": "cha", "level": 3, "name": "wall_of_water", "frequency": "1_per_long_rest", "min_level": 5},
        ],
        "runtime": {
            "triton_gust_of_wind_used": False,
            "triton_wall_of_water_used": False,
            "triton_active_water_wall": None,
        },
    }


def test_triton_create_destroy_water_is_at_will_and_detected() -> None:
    ch = SimpleNamespace(level=1, race_features=_triton_rf(level=1))
    assert ws_handlers._detect_innate_spell_key("кастую создание и уничтожение воды") == "create_or_destroy_water"

    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "create_or_destroy_water")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "create_or_destroy_water")

    assert err_1 is None and err_2 is None
    assert display_name_1 == "Создание/уничтожение воды"
    assert display_name_2 == "Создание/уничтожение воды"
    assert changed_1 is False
    assert changed_2 is False


def test_triton_gust_of_wind_level_gate_and_long_rest_reset() -> None:
    low_level = SimpleNamespace(level=2, race_features=_triton_rf(level=2))
    display_name_low, err_low, changed_low = ws_handlers._apply_innate_spell_usage(low_level, "gust_of_wind")
    assert display_name_low is None
    assert err_low is not None and "3 уровня" in err_low
    assert changed_low is False

    ch = SimpleNamespace(level=3, race_features=_triton_rf(level=3))
    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "gust_of_wind")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "gust_of_wind")

    assert err_1 is None
    assert display_name_1 == "Порыв ветра"
    assert changed_1 is True
    assert display_name_2 is None
    assert err_2 is not None and "долгого отдыха" in err_2
    assert changed_2 is False
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert runtime.get("triton_gust_of_wind_used") is True

    assert ws_handlers._reset_racial_rest_uses(ch, long_rest=True) is True
    runtime_after = (ch.race_features or {}).get("runtime") or {}
    assert runtime_after.get("triton_gust_of_wind_used") is False


def test_triton_wall_of_water_level_gate_long_rest_reset_and_marker() -> None:
    low_level = SimpleNamespace(level=4, race_features=_triton_rf(level=4))
    display_name_low, err_low, changed_low = ws_handlers._apply_innate_spell_usage(low_level, "wall_of_water")
    assert display_name_low is None
    assert err_low is not None and "5 уровня" in err_low
    assert changed_low is False

    ch = SimpleNamespace(level=5, race_features=_triton_rf(level=5))
    display_name_1, err_1, changed_1 = ws_handlers._apply_innate_spell_usage(ch, "wall_of_water")
    display_name_2, err_2, changed_2 = ws_handlers._apply_innate_spell_usage(ch, "wall_of_water")

    assert err_1 is None
    assert display_name_1 == "Стена воды"
    assert changed_1 is True
    assert display_name_2 is None
    assert err_2 is not None and "долгого отдыха" in err_2
    assert changed_2 is False
    runtime = (ch.race_features or {}).get("runtime") or {}
    assert runtime.get("triton_wall_of_water_used") is True
    assert runtime.get("triton_active_water_wall") is not None

    assert ws_handlers._reset_racial_rest_uses(ch, long_rest=True) is True
    runtime_after = (ch.race_features or {}).get("runtime") or {}
    assert runtime_after.get("triton_wall_of_water_used") is False
    assert runtime_after.get("triton_active_water_wall") is None
