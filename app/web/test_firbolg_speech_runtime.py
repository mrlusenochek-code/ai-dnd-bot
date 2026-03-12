from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _FakeDb:
    async def commit(self) -> None:  # pragma: no cover - handler should not need commits here
        raise AssertionError("commit should not be called for firbolg speech utility path")


def _firbolg_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "speech_of_beast_and_leaf": {
                    "type": "limited_beast_plant_speech",
                    "advantage_on": ["cha_checks_to_influence_beasts_plants"],
                }
            }
        },
    )


def _non_firbolg_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}})


def test_firbolg_speech_status_and_narrative_send(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="FirbolgPlayer")
    owner_ch = _firbolg_character(owner_pid, "Фирболг")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    assert ws_handlers._parse_firbolg_speech_command("speech status") == ("firbolg_speech_status", None)
    assert ws_handlers._parse_firbolg_speech_command("speech beast: не бойся нас") == ("firbolg_speech_beast", "не бойся нас")
    assert ws_handlers._parse_firbolg_speech_command("speech plant: укрой нас") == ("firbolg_speech_plant", "укрой нас")

    handled, err, msg = asyncio.run(
        ws_handlers._handle_firbolg_speech_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="firbolg_speech_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "речь зверя и листа" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_firbolg_speech_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="firbolg_speech_beast",
            message_text="не бойся нас",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "простую идею зверю" in msg.lower()

    handled, err, msg = asyncio.run(
        ws_handlers._handle_firbolg_speech_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="firbolg_speech_plant",
            message_text="укрой нас",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and "простую идею растению" in msg.lower()


def test_firbolg_speech_rejects_non_firbolg_and_empty_message(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player_owner = SimpleNamespace(id=owner_pid, display_name="Owner")
    owner_ch = _non_firbolg_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_firbolg_speech_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="firbolg_speech_status",
        )
    )
    assert handled is True
    assert err == "Речь зверя и листа недоступна вашей расе."
    assert msg is None

    owner_ch = _firbolg_character(owner_pid, "Фирболг")

    async def _fake_get_character_firbolg(_db, _sid, pid):
        if pid == owner_pid:
            return owner_ch
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_firbolg)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_firbolg_speech_action(
            _FakeDb(),
            sess,
            player=player_owner,
            action="firbolg_speech_beast",
            message_text="",
        )
    )
    assert handled is True
    assert err == "Укажите простую идею после двоеточия."
    assert msg is None
