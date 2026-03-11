from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _hexblood_with_token() -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "race_key": "hexblood",
            "features": {
                "eerie_token": {
                    "message_words_max": 25,
                    "uses": "per_long_rest",
                    "uses_max": 1,
                }
            },
            "runtime": {
                "eerie_token_uses_used": 1,
                "eerie_token_active": True,
                "eerie_token_consumed": False,
                "eerie_token_id": "et_test1234",
                "eerie_token_created_at": "2026-03-11T12:00:00+00:00",
                "eerie_token_last_message": "",
                "eerie_token_sense_active": False,
                "eerie_token_remote_view_rounds_left": 0,
            },
        }
    )


def test_hexblood_eerie_token_message_requires_active_token_and_word_limit() -> None:
    ch = _hexblood_with_token()

    err_ok, msg_ok, changed_ok = ws_handlers._send_eerie_token_message(
        ch,
        "Это короткое сообщение через жуткий сувенир",
    )
    assert err_ok is None
    assert changed_ok is True
    assert "сообщение отправлено" in (msg_ok or "").lower()
    runtime = ((ch.race_features or {}).get("runtime") or {})
    assert str(runtime.get("eerie_token_last_message") or "").startswith("Это короткое")

    long_message = " ".join([f"слово{i}" for i in range(1, 27)])
    err_long, msg_long, changed_long = ws_handlers._send_eerie_token_message(ch, long_message)
    assert err_long is not None and "25" in err_long
    assert msg_long is None
    assert changed_long is False

    runtime["eerie_token_active"] = False
    runtime["eerie_token_consumed"] = True
    err_missing, msg_missing, changed_missing = ws_handlers._send_eerie_token_message(ch, "поздно")
    assert err_missing == "Нет активного Жуткого сувенира."
    assert msg_missing is None
    assert changed_missing is False
