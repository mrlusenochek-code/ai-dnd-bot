from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers
from app.web.ws_gameplay import _detect_chat_combat_action


def test_detect_shapechanger_chat_actions_and_runtime_cycle() -> None:
    assert _detect_chat_combat_action("меняю внешность на стражника") == "combat_shapechanger_shift"
    assert _detect_chat_combat_action("возвращаюсь в истинную форму") == "combat_shapechanger_revert"

    ch = SimpleNamespace(
        name="Changeling",
        race_features={
            "features": {
                "shapechanger": {"action": True, "revert_on_death": True},
            },
            "runtime": {},
        },
    )

    persona = ws_handlers._extract_shapechanger_persona("меняю внешность на стражника башни")
    assert persona == "стражника башни"

    msg_1, err_1, changed_1 = ws_handlers._apply_shapechanger(ch, active=True, persona=persona, voice="хриплый")
    assert err_1 is None
    assert changed_1 is True
    assert "Меняет облик" in str(msg_1 or "")

    runtime_1 = (ch.race_features or {}).get("runtime") or {}
    shape_1 = runtime_1.get("shapechanger") or {}
    assert shape_1.get("active") is True
    assert shape_1.get("persona") == "стражника башни"

    msg_2, err_2, changed_2 = ws_handlers._apply_shapechanger(ch, active=False)
    assert err_2 is None
    assert changed_2 is True
    assert "истинную форму" in str(msg_2 or "")

    runtime_2 = (ch.race_features or {}).get("runtime") or {}
    shape_2 = runtime_2.get("shapechanger") or {}
    assert shape_2.get("active") is False


def test_shapechanger_history_keeps_last_three_personas() -> None:
    ch = SimpleNamespace(
        name="Changeling",
        race_features={
            "features": {"shapechanger": {"action": True}},
            "runtime": {},
        },
    )
    for persona in ["купец", "часовой", "бард", "служанка"]:
        msg, err, changed = ws_handlers._apply_shapechanger(ch, active=True, persona=persona)
        assert err is None
        assert changed is True
        assert msg is not None

    runtime = (ch.race_features or {}).get("runtime") or {}
    history = runtime.get("shapechanger_history") or []
    personas = [str((x or {}).get("persona") or "") for x in history]
    assert personas == ["часовой", "бард", "служанка"]
