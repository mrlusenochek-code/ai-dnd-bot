from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import app.rules.derived_stats as derived_stats
from app.combat.state import end_combat, get_combat, start_combat, upsert_pc
from app.combat.sync_pcs import sync_pcs_from_chars
from app.rules.equipment_slots import EquipmentSlot
from app.rules.items import ArmorCategory, EquipSpec, ItemDef, ItemKind


def _install_test_armors(monkeypatch) -> None:
    monkeypatch.setitem(
        derived_stats.ITEMS,
        "test_medium_armor",
        ItemDef(
            key="test_medium_armor",
            name_ru="Тестовый средний доспех",
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


def _char(
    *,
    name: str,
    speed_ft: int,
    race_features: dict[str, Any] | None = None,
    inv: list[dict[str, Any]] | None = None,
    equip: dict[str, str] | None = None,
) -> SimpleNamespace:
    inventory = list(inv or [])
    equip_map = dict(equip or {})
    return SimpleNamespace(
        name=name,
        hp=12,
        hp_max=12,
        level=1,
        speed_ft=speed_ft,
        stats={"dex": 50, "_inv": inventory, "_equip": equip_map},
        inventory=inventory,
        equip=equip_map,
        race_features=race_features or {},
    )


def test_shared_sync_pipeline_handles_walk_fly_swim_and_armor_block(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)
    _install_test_armors(monkeypatch)

    medium_inv = [{"id": "armor_m", "def": "test_medium_armor", "name": "Тестовый средний доспех", "qty": 1}]
    medium_equip = {"body": "armor_m"}
    heavy_inv = [{"id": "armor_h", "def": "test_heavy_armor", "name": "Тестовый тяжёлый доспех", "qty": 1}]
    heavy_equip = {"body": "armor_h"}

    chars_by_uid = {
        1: _char(name="Human", speed_ft=30),
        2: _char(
            name="Fairy",
            speed_ft=30,
            race_features={"speeds": {"walk_ft": 30, "fly_ft": 30, "fly_speed_equals_walk": True, "fly_restriction": {"no_armor_categories": ["medium", "heavy"]}}},
        ),
        3: _char(
            name="Owlin",
            speed_ft=30,
            race_features={"speeds": {"walk_ft": 30, "fly_ft": 30, "fly_speed_equals_walk": True, "fly_restriction": {"no_armor_categories": ["medium", "heavy"]}}},
            inv=medium_inv,
            equip=medium_equip,
        ),
        4: _char(
            name="Aarakocra",
            speed_ft=25,
            race_features={"speeds": {"walk_ft": 25, "fly_ft": 50, "fly_restriction": {"no_armor_categories": ["medium", "heavy"]}}},
            inv=heavy_inv,
            equip=heavy_equip,
        ),
        5: _char(
            name="Water Genasi",
            speed_ft=30,
            race_features={"speeds": {"walk_ft": 30, "swim_ft": 30}, "breath": {"amphibious": True}, "features": {"amphibious": True}},
        ),
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 5
    by_name = {str(call["name"]): call for call in calls}

    assert by_name["Human"]["speed_ft"] == 30
    assert by_name["Human"]["movement_speeds"] == {"walk": 30}

    assert by_name["Fairy"]["speed_ft"] == 30
    assert by_name["Fairy"]["movement_speeds"]["walk"] == 30
    assert by_name["Fairy"]["movement_speeds"]["fly"] == 30

    assert by_name["Owlin"]["movement_speeds"]["walk"] == 30
    assert by_name["Owlin"]["movement_speeds"]["fly"] == 0

    assert by_name["Aarakocra"]["speed_ft"] == 15
    assert by_name["Aarakocra"]["movement_speeds"]["walk"] == 15
    assert by_name["Aarakocra"]["movement_speeds"]["fly"] == 0

    assert by_name["Water Genasi"]["speed_ft"] == 30
    assert by_name["Water Genasi"]["movement_speeds"]["walk"] == 30
    assert by_name["Water Genasi"]["movement_speeds"]["swim"] == 30
    assert "fly" not in by_name["Water Genasi"]["movement_speeds"]


def test_shared_sync_pipeline_does_not_double_apply_speed_logic_and_upsert_uses_selected_mode() -> None:
    session_id = "test_shared_sync_pipeline_does_not_double_apply_speed_logic_and_upsert_uses_selected_mode"
    calls: list[dict[str, Any]] = []

    state = start_combat(session_id)
    try:
        fairy = _char(
            name="Fairy",
            speed_ft=30,
            race_features={"speeds": {"walk_ft": 30, "fly_ft": 30, "fly_speed_equals_walk": True, "fly_restriction": {"no_armor_categories": ["medium", "heavy"]}}},
        )

        # Repeated sync should recompute the same movement package instead of accumulating speed.
        def _fake_upsert_pc(sync_session_id: str, **kwargs: Any) -> None:
            calls.append({"session_id": sync_session_id, **kwargs})

        from app.combat import sync_pcs as sync_mod

        original_upsert = sync_mod.upsert_pc
        sync_mod.upsert_pc = _fake_upsert_pc
        try:
            sync_pcs_from_chars(session_id, {1: fairy})
            sync_pcs_from_chars(session_id, {1: fairy})
        finally:
            sync_mod.upsert_pc = original_upsert

        assert len(calls) == 2
        assert calls[0]["movement_speeds"] == {"walk": 30, "fly": 30}
        assert calls[1]["movement_speeds"] == {"walk": 30, "fly": 30}
        assert calls[0]["speed_ft"] == 30
        assert calls[1]["speed_ft"] == 30

        upsert_pc(
            session_id,
            pc_key="pc_fly",
            name="Mode Tester",
            hp=12,
            hp_max=12,
            ac=12,
            speed_ft=30,
            movement_speeds={"walk": 30, "fly": 50, "swim": 30},
            movement_mode="fly",
        )
        upsert_pc(
            session_id,
            pc_key="pc_swim",
            name="Swim Tester",
            hp=12,
            hp_max=12,
            ac=12,
            speed_ft=30,
            movement_speeds={"walk": 30, "swim": 30},
            movement_mode="swim",
        )

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_fly"].move_speed_ft == 50
        assert state_now.combatants["pc_fly"].move_remaining_ft == 50
        assert state_now.combatants["pc_swim"].move_speed_ft == 30
        assert state_now.combatants["pc_swim"].move_remaining_ft == 30
    finally:
        end_combat(session_id)

