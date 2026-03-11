from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _changeling() -> SimpleNamespace:
    return SimpleNamespace(
        name="Changeling",
        race_features={
            "features": {
                "shapechanger": {
                    "action": True,
                    "equipment_unchanged": True,
                    "revert_on_death": True,
                }
            },
            "runtime": {},
        },
    )


def _non_changeling() -> SimpleNamespace:
    return SimpleNamespace(name="Human", race_features={"features": {}, "runtime": {}})


def test_shapechange_assume_status_revert_and_replace() -> None:
    ch = _changeling()

    action, arg = ws_handlers._parse_shapechanger_command("shapechange assume высокий человек с тёмными волосами")
    assert action == "assume"
    assert arg == "высокий человек с тёмными волосами"

    msg_1, err_1, changed_1 = ws_handlers._apply_shapechanger(ch, active=True, persona=arg)
    assert err_1 is None
    assert changed_1 is True
    assert "Меняет облик" in str(msg_1 or "")

    status_err, status_msg, status_changed = ws_handlers._shapechanger_status_message(ch)
    assert status_err is None
    assert status_changed is False
    assert "высокий человек с тёмными волосами" in str(status_msg or "")
    assert "одежда и снаряжение не меняются автоматически" in str(status_msg or "")

    msg_2, err_2, changed_2 = ws_handlers._apply_shapechanger(ch, active=True, persona="низкий бард с хриплым голосом")
    assert err_2 is None
    assert changed_2 is True
    assert "низкий бард" in str(msg_2 or "")

    runtime = (ch.race_features or {}).get("runtime") or {}
    shape = runtime.get("shapechanger") or {}
    assert shape.get("active") is True
    assert shape.get("persona") == "низкий бард с хриплым голосом"

    msg_3, err_3, changed_3 = ws_handlers._apply_shapechanger(ch, active=False)
    assert err_3 is None
    assert changed_3 is True
    assert "истинную форму" in str(msg_3 or "")

    revert_again_msg, revert_again_err, revert_again_changed = ws_handlers._apply_shapechanger(ch, active=False)
    assert revert_again_err is None
    assert revert_again_changed is False
    assert revert_again_msg == "Уже в истинной форме."


def test_shapechange_commands_reject_non_changeling_and_empty_description() -> None:
    outsider = _non_changeling()
    msg, err, changed = ws_handlers._apply_shapechanger(outsider, active=True, persona="страж")
    assert msg is None
    assert err == "Перевёртыш недоступен вашей расе."
    assert changed is False

    action, arg = ws_handlers._parse_shapechanger_command("shapechange assume")
    assert action == "assume"
    assert arg == ""

    action_status, arg_status = ws_handlers._parse_shapechanger_command("shapechange status")
    assert action_status == "status"
    assert arg_status is None
