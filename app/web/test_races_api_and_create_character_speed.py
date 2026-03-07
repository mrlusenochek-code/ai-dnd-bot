from __future__ import annotations

import asyncio
import json
import uuid

from app.web.gameplay_helpers import create_character
from app.web.http_routes import api_races


class _FakeDb:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None


def test_create_character_speed_from_race() -> None:
    db = _FakeDb()

    async def _run():
        return await create_character(
            db,
            session_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            name="Runner",
            class_kit="fighter",
            class_skin="Fighter",
            race_kit="dwarf",
            race_skin="Dwarf",
        )

    ch = asyncio.run(_run())

    assert int(ch.speed_ft) == 25


def test_api_races_nonempty() -> None:
    async def _run():
        return await api_races()

    resp = asyncio.run(_run())
    payload = json.loads(resp.body)
    races = payload.get("races") or []
    assert races
