from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.web import ws_handlers


def _rock_gnome_with_expired() -> SimpleNamespace:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    expired_at = (now - timedelta(hours=1)).isoformat()
    active_at = (now + timedelta(hours=10)).isoformat()
    return SimpleNamespace(
        race_features={
            "race_key": "gnome",
            "subrace": {"key": "rock_gnome"},
            "features": {
                "tinker": {
                    "max_active_devices": 3,
                    "duration_hours": 24,
                    "options": [
                        {"key": "clockwork_toy", "name_ru": "Заводная игрушка"},
                        {"key": "fire_starter", "name_ru": "Зажигалка"},
                        {"key": "music_box", "name_ru": "Музыкальная шкатулка"},
                    ],
                }
            },
            "runtime": {
                "tinker_devices": [
                    {
                        "id": "tk_old1",
                        "type": "clockwork_toy",
                        "name_ru": "Заводная игрушка",
                        "created_at": (now - timedelta(hours=25)).isoformat(),
                        "expires_at": expired_at,
                        "active": True,
                    },
                    {
                        "id": "tk_new1",
                        "type": "music_box",
                        "name_ru": "Музыкальная шкатулка",
                        "created_at": now.isoformat(),
                        "expires_at": active_at,
                        "active": True,
                    },
                ]
            },
        }
    )


def test_rock_gnome_tinker_expired_devices_are_cleaned_up() -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    ch = _rock_gnome_with_expired()

    devices, changed = ws_handlers._cleanup_tinker_devices(ch, now=now)
    assert changed is True
    assert len(devices) == 1
    assert str((devices[0] or {}).get("id") or "") == "tk_new1"

    err, msg, create_changed = ws_handlers._create_tinker_device(ch, "fire_starter", now=now)
    assert err is None
    assert create_changed is True
    assert "Зажигалка" in (msg or "")
