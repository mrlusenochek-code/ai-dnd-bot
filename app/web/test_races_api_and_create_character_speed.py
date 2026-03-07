from __future__ import annotations

import asyncio
import json
import uuid

from app.web.gameplay_helpers import create_character
from app.web.http_routes import api_classes, api_races


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
    race_ids = {str(item.get("id") or "") for item in races if isinstance(item, dict)}
    race_names = {str(item.get("id") or ""): str(item.get("name") or "") for item in races if isinstance(item, dict)}
    assert "human" in race_ids
    assert "aarakocra" in race_ids
    assert "dragonborn" in race_ids
    assert "dwarf" in race_ids
    assert "elf" in race_ids
    assert "genasi" in race_ids
    assert "gnome" in race_ids
    assert "half_elf" in race_ids
    assert "half_orc" in race_ids
    assert "halfling" in race_ids
    assert "tiefling" in race_ids
    assert race_names.get("human") == "Человек"
    assert race_names.get("aarakocra") == "Ааракокра"
    assert race_names.get("genasi") == "Дженази"


def test_api_classes_contains_barbarian() -> None:
    async def _run():
        return await api_classes()

    resp = asyncio.run(_run())
    payload = json.loads(resp.body)
    classes = payload.get("classes") or []
    class_ids = {str(item.get("id") or "") for item in classes if isinstance(item, dict)}
    assert "barbarian" in class_ids
