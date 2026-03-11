from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.web import ws_handlers


def _hexblood() -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "race_key": "hexblood",
            "features": {
                "eerie_token": {
                    "type": "eerie_token",
                    "create_activation": "bonus_action",
                    "range_miles": 10,
                    "message_words_max": 25,
                    "remote_view_duration": "1_minute",
                    "consumes_token_on_view": True,
                    "uses": "per_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {
                "eerie_token_uses_used": 0,
                "eerie_token_active": False,
                "eerie_token_consumed": False,
                "eerie_token_id": "",
                "eerie_token_created_at": "",
                "eerie_token_last_message": "",
                "eerie_token_sense_active": False,
                "eerie_token_remote_view_rounds_left": 0,
                "eerie_token_expires_on_next_long_rest": True,
            },
        }
    )


def _outsider() -> SimpleNamespace:
    return SimpleNamespace(race_features={"race_key": "human", "features": {}, "runtime": {}})


def test_hexblood_eerie_token_create_status_remove_flow() -> None:
    ch = _hexblood()
    now = datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc)

    err_create, msg_create, changed_create = ws_handlers._create_eerie_token(ch, now=now)
    assert err_create is None
    assert changed_create is True
    assert "создан" in (msg_create or "")

    runtime = ((ch.race_features or {}).get("runtime") or {})
    first_id = str(runtime.get("eerie_token_id") or "")
    assert first_id.startswith("et_")
    assert runtime.get("eerie_token_active") is True
    assert int(runtime.get("eerie_token_uses_used") or 0) == 1

    err_replace, msg_replace, changed_replace = ws_handlers._create_eerie_token(ch, now=now)
    assert err_replace is None
    assert changed_replace is True
    assert "заменён" in (msg_replace or "")

    runtime_after_replace = ((ch.race_features or {}).get("runtime") or {})
    second_id = str(runtime_after_replace.get("eerie_token_id") or "")
    assert second_id.startswith("et_")
    assert second_id != first_id
    assert int(runtime_after_replace.get("eerie_token_uses_used") or 0) == 1

    err_status, msg_status, changed_status = ws_handlers._eerie_token_status_message(ch)
    assert err_status is None
    assert changed_status is False
    assert second_id in (msg_status or "")
    assert "активен" in (msg_status or "")

    err_remove, msg_remove, changed_remove = ws_handlers._remove_eerie_token(ch)
    assert err_remove is None
    assert changed_remove is True
    assert second_id in (msg_remove or "")

    runtime_after_remove = ((ch.race_features or {}).get("runtime") or {})
    assert str(runtime_after_remove.get("eerie_token_id") or "") == ""
    assert runtime_after_remove.get("eerie_token_active") is None


def test_hexblood_eerie_token_commands_reject_non_hexblood() -> None:
    outsider = _outsider()

    err_create, msg_create, changed_create = ws_handlers._create_eerie_token(outsider)
    assert err_create == "Жуткий сувенир доступен только ведьминой крови."
    assert msg_create is None
    assert changed_create is False

    err_status, msg_status, changed_status = ws_handlers._eerie_token_status_message(outsider)
    assert err_status == "Жуткий сувенир доступен только ведьминой крови."
    assert msg_status is None
    assert changed_status is False
