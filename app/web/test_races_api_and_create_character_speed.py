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


def test_api_races_names_are_ru_when_available() -> None:
    async def _run():
        return await api_races()

    resp = asyncio.run(_run())
    payload = json.loads(resp.body)
    races = payload.get("races") or []
    assert races
    by_id = {str(item.get("id") or ""): item for item in races if isinstance(item, dict)}
    assert str((by_id.get("human") or {}).get("name") or "") == "Человек"
    assert str((by_id.get("dwarf") or {}).get("name") or "") == "Дварф"
    assert str((by_id.get("elf") or {}).get("name") or "") == "Эльф"
    assert str((by_id.get("verdan") or {}).get("name") or "") == "Вердан"
    assert str((by_id.get("aarakocra") or {}).get("name") or "") == "Ааракокра"

    for race in races:
        if not isinstance(race, dict):
            continue
        details = race.get("details") or {}
        if not isinstance(details, dict):
            continue
        name_ru = str(details.get("name_ru") or "").strip()
        assert name_ru
        assert str(race.get("name") or "") == name_ru


def test_api_classes_contains_barbarian() -> None:
    async def _run():
        return await api_classes()

    resp = asyncio.run(_run())
    payload = json.loads(resp.body)
    classes = payload.get("classes") or []
    class_ids = {str(item.get("id") or "") for item in classes if isinstance(item, dict)}
    assert "barbarian" in class_ids
