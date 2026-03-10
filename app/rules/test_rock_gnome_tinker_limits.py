from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.web import ws_handlers


def _rock_gnome() -> SimpleNamespace:
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
            "runtime": {"tinker_devices": []},
        }
    )


def test_rock_gnome_tinker_allows_only_three_active_devices() -> None:
    ch = _rock_gnome()
    now = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)

    assert ws_handlers._create_tinker_device(ch, "clockwork_toy", now=now)[0] is None
    assert ws_handlers._create_tinker_device(ch, "fire_starter", now=now)[0] is None
    assert ws_handlers._create_tinker_device(ch, "music_box", now=now)[0] is None

    err, msg, changed = ws_handlers._create_tinker_device(ch, "clockwork_toy", now=now)
    assert err == "У вас уже есть 3 активных устройства гномьего механика. Сначала разберите одно из них."
    assert msg is None
    assert changed is False
