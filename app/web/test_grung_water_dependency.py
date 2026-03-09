from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_grung_water_dependency_long_rest_and_immersion_cycle() -> None:
    ch = SimpleNamespace(
        race_features={
            "race_key": "grung",
            "features": {
                "water_dependency": {
                    "required_immersion_per_day": "1_hour",
                    "penalty": "exhaustion_1",
                }
            },
            "runtime": {},
        }
    )

    t0 = datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc)

    level_1, changed_1 = ws_handlers._apply_grung_water_dependency_long_rest(ch, now=t0)
    assert changed_1 is True
    assert level_1 == 1
    runtime_1 = (ch.race_features or {}).get("runtime") or {}
    assert int(runtime_1.get("water_dependency_exhaustion_level") or 0) == 1

    immersion_iso, water_level, immersion_err, immersion_changed = ws_handlers._apply_grung_water_immersion(
        ch,
        now=t0 + timedelta(hours=1),
    )
    assert immersion_err is None
    assert immersion_changed is True
    assert isinstance(immersion_iso, str) and immersion_iso
    assert int(water_level or 0) == 0

    runtime_2 = (ch.race_features or {}).get("runtime") or {}
    assert str(runtime_2.get("water_last_immersion_at") or "") == immersion_iso
    assert int(runtime_2.get("water_dependency_exhaustion_level") or 0) == 0

    level_2, changed_2 = ws_handlers._apply_grung_water_dependency_long_rest(ch, now=t0 + timedelta(hours=2))
    assert changed_2 is True
    assert level_2 == 0

    level_3, changed_3 = ws_handlers._apply_grung_water_dependency_long_rest(ch, now=t0 + timedelta(hours=27))
    assert changed_3 is True
    assert level_3 == 1


def test_grung_water_and_weapon_poison_regex_actions() -> None:
    assert _detect_chat_combat_action("смазываю оружие ядом") == "combat_grung_poison_weapon"
    assert _detect_chat_combat_action("apply poison") == "combat_grung_poison_weapon"
    assert _detect_chat_combat_action("погружаюсь в воду") == "water_immerse"
    assert _detect_chat_combat_action("immerse in water") == "water_immerse"
