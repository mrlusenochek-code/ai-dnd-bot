from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.web import server


def test_build_player_gm_action_text_moved_true_contains_location_before_action(monkeypatch) -> None:
    sess = SimpleNamespace(settings={})

    monkeypatch.setattr(server, "_apply_world_move_from_text", lambda _sess, _sid, _text: ("иду на север", True))
    monkeypatch.setattr(server.narration, "build_location_block", lambda _settings, _sid: "ЛОКАЦИЯ-БЛОК")

    async def fake_encounter(_db, _sess, _sid):
        return None, ""

    monkeypatch.setattr(server, "_maybe_start_encounter_after_move", fake_encounter)

    gm_action_text, moved, encounter_patch = asyncio.run(
        server._build_player_gm_action_text(
            SimpleNamespace(),
            sess,
            "sess_test",
            "шаг вперед",
            include_encounter_after_move=False,
        )
    )

    assert moved is True
    assert encounter_patch is None
    assert "ТЕКУЩАЯ ЛОКАЦИЯ:\nЛОКАЦИЯ-БЛОК" in gm_action_text
    assert "ДЕЙСТВИЕ ИГРОКА:\nиду на север" in gm_action_text
    assert gm_action_text.find("ТЕКУЩАЯ ЛОКАЦИЯ:\nЛОКАЦИЯ-БЛОК") < gm_action_text.find("ДЕЙСТВИЕ ИГРОКА:\nиду на север")


def test_build_player_gm_action_text_moved_false_still_contains_location_block(monkeypatch) -> None:
    sess = SimpleNamespace(settings={})

    monkeypatch.setattr(server, "_apply_world_move_from_text", lambda _sess, _sid, _text: ("осматриваюсь", False))
    monkeypatch.setattr(server.narration, "build_location_block", lambda _settings, _sid: "ЛОКАЦИЯ-БЛОК")

    async def fake_encounter(_db, _sess, _sid):
        return None, ""

    monkeypatch.setattr(server, "_maybe_start_encounter_after_move", fake_encounter)

    gm_action_text, moved, encounter_patch = asyncio.run(
        server._build_player_gm_action_text(
            SimpleNamespace(),
            sess,
            "sess_test",
            "осматриваюсь",
            include_encounter_after_move=False,
        )
    )

    assert moved is False
    assert encounter_patch is None
    assert "ТЕКУЩАЯ ЛОКАЦИЯ:\nЛОКАЦИЯ-БЛОК" in gm_action_text
    assert "ДЕЙСТВИЕ ИГРОКА:\nосматриваюсь" in gm_action_text


def test_build_player_gm_action_text_encounter_after_move_uses_narration_builder(monkeypatch) -> None:
    sess = SimpleNamespace(settings={})
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(server, "_apply_world_move_from_text", lambda _sess, _sid, _text: ("иду к воротам", True))

    def fake_build_gm_input_text(settings, session_id, player_text, *, moved):
        calls.append({"settings": settings, "session_id": session_id, "player_text": player_text, "moved": moved})
        return "GM_INPUT_BASE"

    monkeypatch.setattr(server.narration, "build_gm_input_text", fake_build_gm_input_text)

    async def fake_encounter(_db, _sess, _sid):
        return {"open": True}, "ВОЗМОЖНА ВСТРЕЧА."

    monkeypatch.setattr(server, "_maybe_start_encounter_after_move", fake_encounter)

    gm_action_text, moved, encounter_patch = asyncio.run(
        server._build_player_gm_action_text(
            SimpleNamespace(),
            sess,
            "sess_test",
            "иду",
            include_encounter_after_move=True,
        )
    )

    assert moved is True
    assert encounter_patch == {"open": True}
    assert calls == [{"settings": sess.settings, "session_id": "sess_test", "player_text": "иду к воротам", "moved": True}]
    assert gm_action_text == "GM_INPUT_BASE\n\nВОЗМОЖНА ВСТРЕЧА."
