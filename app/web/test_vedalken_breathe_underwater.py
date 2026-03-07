from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.rules.character_catalog import resolve_race
from app.web import http_routes, ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_vedalken_breathe_underwater_persist_and_runtime_cycle() -> None:
    vedalken = resolve_race("vedalken")
    assert isinstance(vedalken, dict)

    race_features = http_routes._build_race_features(vedalken)
    breath = race_features.get("breath") or {}
    underwater = breath.get("underwater") or {}
    assert int(underwater.get("duration_seconds") or 0) == 3600
    assert str(underwater.get("uses") or "") == "per_long_rest"

    action = _detect_chat_combat_action("дышу под водой")
    assert action == "breathe_underwater"

    ch = SimpleNamespace(name="Vedalken", race_features=race_features)
    t0 = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)

    until_1, hhmm_1, err_1, changed_1 = ws_handlers._apply_breathe_underwater_usage(ch, now=t0)
    assert err_1 is None
    assert changed_1 is True
    assert isinstance(until_1, str) and until_1
    assert isinstance(hhmm_1, str) and hhmm_1
    runtime_1 = (ch.race_features or {}).get("runtime") or {}
    assert runtime_1.get("breathe_underwater_used") is True
    assert str(runtime_1.get("breathe_underwater_until_iso") or "") == until_1

    until_2, hhmm_2, err_2, changed_2 = ws_handlers._apply_breathe_underwater_usage(ch, now=t0 + timedelta(minutes=10))
    assert until_2 is None
    assert hhmm_2 is None
    assert changed_2 is False
    assert err_2 is not None
    assert "уже активно" in err_2

    until_3, hhmm_3, err_3, changed_3 = ws_handlers._apply_breathe_underwater_usage(ch, now=t0 + timedelta(hours=2))
    assert until_3 is None
    assert hhmm_3 is None
    assert changed_3 is False
    assert err_3 is not None
    assert "долгого отдыха" in err_3

    reset_changed = ws_handlers._reset_racial_rest_uses(ch)
    assert reset_changed is True
    runtime_after_reset = (ch.race_features or {}).get("runtime") or {}
    assert "breathe_underwater_used" not in runtime_after_reset
    assert "breathe_underwater_until_iso" not in runtime_after_reset

    until_4, hhmm_4, err_4, changed_4 = ws_handlers._apply_breathe_underwater_usage(ch, now=t0 + timedelta(hours=2))
    assert err_4 is None
    assert changed_4 is True
    assert isinstance(until_4, str) and until_4
    assert isinstance(hhmm_4, str) and hhmm_4
