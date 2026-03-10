from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.web import ws_handlers


def _rock_gnome() -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "race_key": "gnome",
            "subrace": {"key": "rock_gnome"},
            "features": {
                "tinker": {
                    "tool_proficiency": "tinkers_tools",
                    "max_active_devices": 3,
                    "duration_hours": 24,
                    "options": [
                        {"key": "clockwork_toy", "name_ru": "Заводная игрушка"},
                        {"key": "fire_starter", "name_ru": "Зажигалка"},
                        {"key": "music_box", "name_ru": "Музыкальная шкатулка"},
                    ],
                }
            },
            "proficiencies": {"tools": ["tinkers_tools"]},
            "runtime": {"tinker_devices": []},
        }
    )


def _non_rock_gnome() -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "race_key": "gnome",
            "subrace": {"key": "forest_gnome"},
            "features": {},
            "runtime": {},
        }
    )


def test_rock_gnome_tinker_create_list_remove_flow() -> None:
    ch = _rock_gnome()
    now = datetime(2026, 3, 10, 21, 30, tzinfo=timezone.utc)

    err1, msg1, changed1 = ws_handlers._create_tinker_device(ch, "clockwork_toy", now=now)
    err2, msg2, changed2 = ws_handlers._create_tinker_device(ch, "fire_starter", now=now)
    err3, msg3, changed3 = ws_handlers._create_tinker_device(ch, "music_box", now=now)

    assert err1 is None and err2 is None and err3 is None
    assert changed1 is True and changed2 is True and changed3 is True
    assert "Заводная игрушка" in (msg1 or "")
    assert "Зажигалка" in (msg2 or "")
    assert "Музыкальная шкатулка" in (msg3 or "")

    list_err, list_msg, list_changed = ws_handlers._list_tinker_devices(ch, now=now)
    assert list_err is None
    assert list_changed is False
    assert "[TINKER] Активные устройства:" in (list_msg or "")

    devices = ((ch.race_features or {}).get("runtime") or {}).get("tinker_devices") or []
    device_id = str((devices[0] or {}).get("id") or "")
    remove_err, remove_msg, remove_changed = ws_handlers._remove_tinker_device(ch, device_id, now=now)
    assert remove_err is None
    assert remove_changed is True
    assert device_id in (remove_msg or "")


def test_rock_gnome_tinker_rejects_non_rock_gnome_and_invalid_type() -> None:
    outsider = _non_rock_gnome()
    err_out, msg_out, changed_out = ws_handlers._create_tinker_device(outsider, "clockwork_toy")
    assert err_out == "Гномий механик доступен только скальному гному."
    assert msg_out is None
    assert changed_out is False

    ch = _rock_gnome()
    err_bad, msg_bad, changed_bad = ws_handlers._create_tinker_device(ch, "bad_device")
    assert err_bad is not None and "Неизвестный тип устройства" in err_bad
    assert msg_bad is None
    assert changed_bad is False
