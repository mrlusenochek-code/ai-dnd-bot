from __future__ import annotations

import asyncio
import copy
import uuid
from types import SimpleNamespace

from app.web import ws_handlers


class _CountingDb:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _verdan_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "limited_telepathy": {
                    "range_ft": 30,
                    "requires_target_language": True,
                    "bandwidth": "simple_ideas",
                }
            },
            "senses": {
                "telepathy": {
                    "range_ft": 30,
                    "requires_target_language": True,
                    "bandwidth": "simple_ideas",
                }
            },
            "runtime": {},
        },
    )


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


def _kenku_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "mimicry": {
                    "type": "mimicry",
                    "counter_check": {"ability": "wis", "skill": "insight"},
                },
                "expert_forgery": {
                    "type": "expert_forgery",
                },
            }
        },
    )


def _loxodon_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        player_id=player_id,
        race_features={
            "features": {
                "trunk": {
                    "type": "trunk",
                    "reach_ft": 5,
                    "lift_lb_formula": "5*str",
                    "cannot": ["wield_weapons", "wield_shield", "fine_manipulation", "somatic_components"],
                }
            }
        },
    )


def _plain_character(player_id: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, player_id=player_id, race_features={"features": {}, "runtime": {}})


def test_shared_utility_pipeline_alias_parsers_match_canonical_commands() -> None:
    assert ws_handlers._parse_verdan_telepathy_command("telepathy status") == ws_handlers._parse_verdan_telepathy_command("телепатия статус")
    assert ws_handlers._parse_verdan_telepathy_command("telepathy send Лира: привет") == ws_handlers._parse_verdan_telepathy_command("телепатия отправить Лира: привет")

    assert ws_handlers._parse_firbolg_speech_command("speech beast: тише") == ("firbolg_speech_beast", "тише")
    assert ws_handlers._parse_firbolg_speech_command("речь зверю: тише") == ("firbolg_speech_beast", "тише")
    assert ws_handlers._parse_firbolg_speech_command("speech plant: укрой") == ("firbolg_speech_plant", "укрой")
    assert ws_handlers._parse_firbolg_speech_command("речь растению: укрой") == ("firbolg_speech_plant", "укрой")

    assert ws_handlers._parse_kenku_mimicry_command("mimicry voice: уходите") == ("kenku_mimicry_voice", "уходите")
    assert ws_handlers._parse_kenku_mimicry_command("подражание голос: уходите") == ("kenku_mimicry_voice", "уходите")
    assert ws_handlers._parse_kenku_mimicry_command("mimicry sound: щелчок") == ("kenku_mimicry_sound", "щелчок")
    assert ws_handlers._parse_kenku_mimicry_command("подражание звук: щелчок") == ("kenku_mimicry_sound", "щелчок")

    assert ws_handlers._parse_kenku_expert_forgery_command("forgery copy: подпись") == ("kenku_forgery_copy", "подпись")
    assert ws_handlers._parse_kenku_expert_forgery_command("подлог: подпись") == ("kenku_forgery_copy", "подпись")

    assert ws_handlers._parse_loxodon_trunk_command("trunk use: открыть дверь") == ("loxodon_trunk_use", "открыть дверь")
    assert ws_handlers._parse_loxodon_trunk_command("хобот: открыть дверь") == ("loxodon_trunk_use", "открыть дверь")


def test_shared_utility_pipeline_status_commands_are_read_only(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player = SimpleNamespace(id=owner_pid, display_name="Owner")
    target_player = SimpleNamespace(id=target_pid, display_name="Scout")

    verdan = _verdan_character(owner_pid, "Вердан")
    firbolg = _firbolg_character(owner_pid, "Фирболг")
    kenku = _kenku_character(owner_pid, "Кенку")
    loxodon = _loxodon_character(owner_pid, "Локсодон")
    target = SimpleNamespace(name="Лира", player_id=target_pid, race_features={"runtime": {}})

    before_verdan = copy.deepcopy(verdan.race_features)
    db = _CountingDb()

    async def _fake_get_character_verdan(_db, _sid, pid):
        return verdan if pid == owner_pid else None

    async def _fake_load_actor_context(_db, _sess):
        uid_map = {
            101: (SimpleNamespace(player_id=owner_pid), player),
            202: (SimpleNamespace(player_id=target_pid), target_player),
        }
        return uid_map, {101: verdan, 202: target}, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character_verdan)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            db,
            sess,
            player=player,
            session_id="utility-status",
            action="verdan_telepathy_status",
        )
    )
    assert handled is True
    assert err is None
    assert msg is not None and msg.count("[RACE]") == 1
    assert verdan.race_features == before_verdan
    assert db.commits == 0

    for character, handler, action, message_text in (
        (firbolg, ws_handlers._handle_firbolg_speech_action, "firbolg_speech_status", ""),
        (kenku, ws_handlers._handle_kenku_mimicry_action, "kenku_mimicry_status", ""),
        (kenku, ws_handlers._handle_kenku_expert_forgery_action, "kenku_forgery_status", ""),
        (loxodon, ws_handlers._handle_loxodon_trunk_action, "loxodon_trunk_status", ""),
    ):
        async def _fake_get_character(_db, _sid, pid, character=character):
            return character if pid == owner_pid else None

        monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
        before = copy.deepcopy(character.race_features)
        handled, err, msg = asyncio.run(handler(db, sess, player=player, action=action, message_text=message_text))
        assert handled is True
        assert err is None
        assert msg is not None and msg.count("[RACE]") == 1
        assert character.race_features == before
        assert db.commits == 0


def test_shared_utility_pipeline_feature_gated_commands_emit_consistent_narrative_events(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    target_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player = SimpleNamespace(id=owner_pid, display_name="Owner")
    target_player = SimpleNamespace(id=target_pid, display_name="Scout")

    verdan = _verdan_character(owner_pid, "Вердан")
    firbolg = _firbolg_character(owner_pid, "Фирболг")
    kenku = _kenku_character(owner_pid, "Кенку")
    loxodon = _loxodon_character(owner_pid, "Локсодон")
    target = SimpleNamespace(name="Лира", player_id=target_pid, race_features={"runtime": {}})

    db = _CountingDb()

    async def _fake_load_actor_context(_db, _sess):
        uid_map = {
            101: (SimpleNamespace(player_id=owner_pid), player),
            202: (SimpleNamespace(player_id=target_pid), target_player),
        }
        return uid_map, {101: verdan, 202: target}, {}

    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    async def _fake_get_character(_db, _sid, pid):
        if pid != owner_pid:
            return None
        if getattr(_fake_get_character, "mode", "") == "verdan":
            return verdan
        if getattr(_fake_get_character, "mode", "") == "firbolg":
            return firbolg
        if getattr(_fake_get_character, "mode", "") == "kenku":
            return kenku
        if getattr(_fake_get_character, "mode", "") == "loxodon":
            return loxodon
        return None

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)

    _fake_get_character.mode = "verdan"
    handled, err, msg = asyncio.run(
        ws_handlers._handle_verdan_limited_telepathy_action(
            db,
            sess,
            player=player,
            session_id="utility-send",
            action="verdan_telepathy_send",
            target_name="Лира",
            message_text="держимся вместе",
        )
    )
    assert handled is True
    assert err is None
    assert msg == "[RACE] Ограниченная телепатия → Лира: держимся вместе"
    verdan_runtime = (verdan.race_features or {}).get("runtime") or {}
    assert str(verdan_runtime.get("verdan_telepathy_last_target") or "") == "Лира"
    assert db.commits == 1

    for mode, handler, action, text, expected in (
        ("firbolg", ws_handlers._handle_firbolg_speech_action, "firbolg_speech_beast", "не бойся", "простую идею зверю"),
        ("firbolg", ws_handlers._handle_firbolg_speech_action, "firbolg_speech_plant", "укрой нас", "простую идею растению"),
        ("kenku", ws_handlers._handle_kenku_mimicry_action, "kenku_mimicry_voice", "уходите", "имитируете голос"),
        ("kenku", ws_handlers._handle_kenku_mimicry_action, "kenku_mimicry_sound", "скрип двери", "имитируете звук"),
        ("kenku", ws_handlers._handle_kenku_expert_forgery_action, "kenku_forgery_copy", "подпись старосты", "тщательно воспроизводите"),
        ("loxodon", ws_handlers._handle_loxodon_trunk_action, "loxodon_trunk_use", "открыть ворота", "используете хобот"),
    ):
        _fake_get_character.mode = mode
        before_commits = db.commits
        handled, err, msg = asyncio.run(handler(db, sess, player=player, action=action, message_text=text))
        assert handled is True
        assert err is None
        assert msg is not None and msg.startswith("[RACE] ")
        assert msg.count("[RACE]") == 1
        assert expected in msg.lower()
        assert db.commits == before_commits


def test_shared_utility_pipeline_rejects_missing_feature_consistently(monkeypatch) -> None:
    owner_pid = uuid.uuid4()
    sess = SimpleNamespace(id=uuid.uuid4())
    player = SimpleNamespace(id=owner_pid, display_name="Owner")
    plain = _plain_character(owner_pid, "Human")

    async def _fake_get_character(_db, _sid, pid):
        return plain if pid == owner_pid else None

    async def _fake_load_actor_context(_db, _sess):
        return {101: (SimpleNamespace(player_id=owner_pid), player)}, {101: plain}, {}

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_load_actor_context", _fake_load_actor_context)

    db = _CountingDb()
    for coro, expected_err in (
        (
            ws_handlers._handle_verdan_limited_telepathy_action(
                db,
                sess,
                player=player,
                session_id="utility-reject",
                action="verdan_telepathy_send",
                target_name="Лира",
                message_text="привет",
            ),
            "Ограниченная телепатия недоступна вашей расе.",
        ),
        (
            ws_handlers._handle_firbolg_speech_action(
                db,
                sess,
                player=player,
                action="firbolg_speech_status",
            ),
            "Речь зверя и листа недоступна вашей расе.",
        ),
        (
            ws_handlers._handle_kenku_mimicry_action(
                db,
                sess,
                player=player,
                action="kenku_mimicry_status",
            ),
            "Подражание недоступно вашей расе.",
        ),
        (
            ws_handlers._handle_kenku_expert_forgery_action(
                db,
                sess,
                player=player,
                action="kenku_forgery_status",
            ),
            "Искусный подлог недоступен вашей расе.",
        ),
        (
            ws_handlers._handle_loxodon_trunk_action(
                db,
                sess,
                player=player,
                action="loxodon_trunk_status",
            ),
            "Хобот недоступен вашей расе.",
        ),
    ):
        handled, err, msg = asyncio.run(coro)
        assert handled is True
        assert err == expected_err
        assert msg is None
    assert db.commits == 0
