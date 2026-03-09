from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_locathah_limited_amphibious_status_and_immersion_cycle() -> None:
    ch = SimpleNamespace(
        race_features={
            "race_key": "locathah",
            "features": {"limited_amphibious": {"must_immerse_every": "4_hours"}},
            "runtime": {},
        }
    )

    t0 = datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc)

    hours_1, suff_1, changed_1 = ws_handlers._apply_locathah_limited_amphibious_status(ch, now=t0)
    assert changed_1 is True
    assert suff_1 is True
    assert float(hours_1) > 4.0

    immersion_iso, hours_2, suff_2, immersion_err, immersion_changed = ws_handlers._apply_locathah_water_immersion(
        ch,
        now=t0 + timedelta(minutes=10),
    )
    assert immersion_err is None
    assert immersion_changed is True
    assert isinstance(immersion_iso, str) and immersion_iso
    assert float(hours_2 or 0.0) == 0.0
    assert suff_2 is False

    runtime = (ch.race_features or {}).get("runtime") or {}
    assert str(runtime.get("water_last_immersion_at") or "") == immersion_iso
    assert bool(runtime.get("suffocating")) is False

    hours_3, suff_3, changed_3 = ws_handlers._apply_locathah_limited_amphibious_status(ch, now=t0 + timedelta(hours=5))
    assert changed_3 is True
    assert float(hours_3) > 4.0
    assert suff_3 is True


def test_locathah_water_immerse_regex_action() -> None:
    assert _detect_chat_combat_action("погружаюсь в воду") == "water_immerse"
    assert _detect_chat_combat_action("immerse in water") == "water_immerse"
