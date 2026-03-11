from __future__ import annotations

import app.rules.derived_stats as derived_stats
from app.rules.derived_stats import fly_speed_available_by_armor
from app.rules.equipment_slots import EquipmentSlot
from app.rules.items import ArmorCategory, EquipSpec, ItemDef, ItemKind


def test_owlin_fly_speed_available_without_restricted_armor() -> None:
    race_features = {
        "speeds": {
            "walk_ft": 30,
            "fly_ft": 30,
            "fly_speed_equals_walk": True,
            "fly_restriction": {"no_armor_categories": ["medium", "heavy"]},
        }
    }

    available, armor_cat = fly_speed_available_by_armor(
        race_features=race_features,
        inventory=[],
        equip_map={},
    )

    assert available is True
    assert armor_cat is None
    assert race_features["speeds"]["fly_ft"] == 30
    assert race_features["speeds"]["fly_speed_equals_walk"] is True


def test_owlin_fly_speed_blocked_in_medium_armor(monkeypatch) -> None:
    race_features = {
        "speeds": {
            "walk_ft": 30,
            "fly_ft": 30,
            "fly_speed_equals_walk": True,
            "fly_restriction": {"no_armor_categories": ["medium", "heavy"]},
        }
    }
    monkeypatch.setitem(
        derived_stats.ITEMS,
        "test_medium_armor",
        ItemDef(
            key="test_medium_armor",
            name_ru="Средний доспех",
            kind=ItemKind.armor,
            equip=EquipSpec(
                allowed_slots=(EquipmentSlot.body,),
                wear_group="armor",
                armor_category=ArmorCategory.medium,
                base_ac=12,
            ),
            description_ru="Тестовый средний доспех.",
        ),
    )

    available, armor_cat = fly_speed_available_by_armor(
        race_features=race_features,
        inventory=[{"id": "armor1", "def": "test_medium_armor", "name": "Средний доспех", "qty": 1}],
        equip_map={"body": "armor1"},
    )

    assert available is False
    assert armor_cat == "medium"


def test_owlin_fly_speed_blocked_in_heavy_armor(monkeypatch) -> None:
    race_features = {
        "speeds": {
            "walk_ft": 30,
            "fly_ft": 30,
            "fly_speed_equals_walk": True,
            "fly_restriction": {"no_armor_categories": ["medium", "heavy"]},
        }
    }
    monkeypatch.setitem(
        derived_stats.ITEMS,
        "test_heavy_armor",
        ItemDef(
            key="test_heavy_armor",
            name_ru="Тяжёлый доспех",
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

    available, armor_cat = fly_speed_available_by_armor(
        race_features=race_features,
        inventory=[{"id": "armor1", "def": "test_heavy_armor", "name": "Тяжёлый доспех", "qty": 1}],
        equip_map={"body": "armor1"},
    )

    assert available is False
    assert armor_cat == "heavy"


def test_non_owlin_without_flight_is_unchanged() -> None:
    available, armor_cat = fly_speed_available_by_armor(
        race_features={"speeds": {"walk_ft": 30}},
        inventory=[],
        equip_map={},
    )

    assert available is False
    assert armor_cat is None
