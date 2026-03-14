from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.web import state_builder


class _FakeScalarResult:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class _FakeExecuteResult:
    def __init__(self, items):
        self._items = list(items)

    def scalars(self):
        return _FakeScalarResult(self._items)


class _FakeDb:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _query):
        if not self._responses:
            raise AssertionError("unexpected execute call")
        return _FakeExecuteResult(self._responses.pop(0))


def test_build_state_includes_legacy_and_structured_positions(monkeypatch) -> None:
    player_id = uuid.uuid4()
    session_id = uuid.uuid4()
    char_id = uuid.uuid4()
    structured_position = {
        "v": 1,
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }

    sess = SimpleNamespace(
        id=session_id,
        title="Campaign",
        is_active=False,
        is_paused=False,
        turn_index=0,
        current_player_id=None,
        turn_started_at=None,
        settings={},
    )
    sp = SimpleNamespace(player_id=player_id, join_order=1, is_admin=False, is_active=True)
    player = SimpleNamespace(id=player_id, display_name="Alice", web_user_id=42, telegram_user_id=None)
    char = SimpleNamespace(
        id=char_id,
        session_id=session_id,
        player_id=player_id,
        name="Рин",
        level=2,
        stats={},
        hp=10,
        hp_max=12,
        sta=5,
        sta_max=6,
    )

    async def fake_list_session_players(_db, _sess, active_only=False):
        assert active_only is False
        return [sp]

    monkeypatch.setattr(state_builder, "list_session_players", fake_list_session_players)
    monkeypatch.setattr(state_builder, "_get_kicked", lambda _sess: set())
    monkeypatch.setattr(state_builder, "_char_to_payload", lambda _char: {"name": _char.name} if _char else None)
    monkeypatch.setattr(state_builder, "_level_progress_payload", lambda _char: {"level": _char.level})
    monkeypatch.setattr(state_builder, "_skills_payload_for_character", lambda _char, _skills: [])
    monkeypatch.setattr(state_builder, "_player_uid", lambda _player: _player.web_user_id)
    monkeypatch.setattr(state_builder, "_get_ready_map", lambda _sess: {str(player_id): True})
    monkeypatch.setattr(state_builder, "_get_init_map", lambda _sess: {str(player_id): 7})
    monkeypatch.setattr(state_builder, "_get_last_seen_map", lambda _sess: {str(player_id): "2026-03-14T00:00:00"})
    monkeypatch.setattr(state_builder, "_initiative_fixed", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_is_free_turns", lambda _sess: False)
    monkeypatch.setattr(state_builder, "_get_phase", lambda _sess: "turns")
    monkeypatch.setattr(state_builder, "_get_round_actions", lambda _sess: {})
    monkeypatch.setattr(state_builder, "_ready_active_players", lambda _sess, active_sps: active_sps)
    monkeypatch.setattr(state_builder, "_get_pc_positions", lambda _sess: {str(player_id): "Старый подвал"})
    monkeypatch.setattr(state_builder, "_get_map_positions", lambda _sess: {str(player_id): structured_position})
    monkeypatch.setattr(state_builder, "snapshot_combat_state", lambda _session_id: None)

    db = _FakeDb([[player], [char], [], []])
    payload = asyncio.run(state_builder.build_state(db, sess))

    assert payload["game"]["pc_positions"] == {"42": "Старый подвал"}
    assert payload["game"]["map_positions"] == {"42": structured_position}
    assert payload["players"] == [
        {
            "id": str(player_id),
            "uid": 42,
            "name": "Alice",
            "order": 1,
            "is_admin": False,
            "is_current": False,
            "is_active": True,
            "is_ready": True,
            "initiative": 7,
            "last_seen": "2026-03-14T00:00:00",
            "char": {"name": "Рин", "level_progress": {"level": 2}, "skills": []},
            "has_character": True,
            "zone": "Старый подвал",
            "map_position": structured_position,
        }
    ]
