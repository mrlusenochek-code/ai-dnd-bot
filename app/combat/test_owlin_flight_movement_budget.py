from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import app.rules.derived_stats as derived_stats
from app.combat.sync_pcs import sync_pcs_from_chars
from app.rules.equipment_slots import EquipmentSlot
from app.rules.items import ArmorCategory, EquipSpec, ItemDef, ItemKind


def test_owlin_flight_enters_combat_movement_speeds(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    chars_by_uid = {
        1: SimpleNamespace(
            name="Owlin",
            hp=12,
            hp_max=12,
            level=1,
            speed_ft=30,
            stats={"dex": 60, "_inv": [], "_equip": {}},
            inventory=[],
            equip={},
            race_features={
                "speeds": {
                    "walk_ft": 30,
                    "fly_ft": 30,
                    "fly_speed_equals_walk": True,
                    "fly_restriction": {"no_armor_categories": ["medium", "heavy"]},
                }
            },
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["speed_ft"] == 30
    assert calls[0]["movement_speeds"]["walk"] == 30
    assert calls[0]["movement_speeds"]["fly"] == 30


def test_owlin_flight_blocked_in_heavy_armor_for_combat_movement(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)
    monkeypatch.setitem(
        derived_stats.ITEMS,
        "test_heavy_armor",
        ItemDef(
            key="test_heavy_armor",
            name_ru="Тестовый тяжёлый доспех",
            kind=ItemKind.armor,
            equip=EquipSpec(
                allowed_slots=(EquipmentSlot.body,),
                wear_group="armor",
                armor_category=ArmorCategory.heavy,
                base_ac=16,
            ),
            description_ru="Тестовый тяжёлый доспех.",
        ),
    )

    chars_by_uid = {
        1: SimpleNamespace(
            name="Owlin",
            hp=12,
            hp_max=12,
            level=1,
            speed_ft=30,
            stats={
                "dex": 60,
                "_inv": [{"id": "armor1", "def": "test_heavy_armor", "name": "Тестовый тяжёлый доспех", "qty": 1}],
                "_equip": {"body": "armor1"},
            },
            inventory=[{"id": "armor1", "def": "test_heavy_armor", "name": "Тестовый тяжёлый доспех", "qty": 1}],
            equip={"body": "armor1"},
            race_features={
                "speeds": {
                    "walk_ft": 30,
                    "fly_ft": 30,
                    "fly_speed_equals_walk": True,
                    "fly_restriction": {"no_armor_categories": ["medium", "heavy"]},
                }
            },
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["movement_speeds"]["walk"] == 30
    assert calls[0]["movement_speeds"]["fly"] == 0
