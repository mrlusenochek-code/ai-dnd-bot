from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.combat.sync_pcs import sync_pcs_from_chars


def test_sync_pcs_from_chars_non_dict_stats_uses_phb_fallback_ac(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    chars_by_uid = {
        1: SimpleNamespace(
            name="Alice",
            hp=10,
            hp_max=10,
            level=1,
            speed_ft=35,
            stats=None,
            class_features={"features": [{"key": "sneak_attack"}], "runtime": {}},
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["ac"] == 10
    assert calls[0]["speed_ft"] == 35
    assert calls[0]["class_features"] == {"features": [{"key": "sneak_attack"}], "runtime": {}}


def test_sync_pcs_from_chars_updates_existing_combatant_inventory_and_equip() -> None:
    from app.combat.state import end_combat, get_combat, start_combat, upsert_pc

    session_id = "test_sync_updates_existing_inventory_and_equip"
    start_combat(session_id)
    try:
        upsert_pc(
            session_id,
            pc_key="pc_1",
            name="Alice",
            hp=10,
            hp_max=10,
            ac=10,
            initiative=0,
            inventory=[],
            equip={},
        )

        chars_by_uid = {
            1: SimpleNamespace(
                name="Alice",
                hp=10,
                hp_max=10,
                level=5,
                speed_ft=30,
                stats={
                    "str": 50,
                    "dex": 70,
                    "con": 50,
                    "_inv": [
                        {"id": "dagger_main", "name": "Кинжал", "qty": 1, "def": "dagger"},
                        {"id": "dagger_off", "name": "Кинжал", "qty": 1, "def": "dagger"},
                    ],
                    "_equip": {"main_hand": "dagger_main", "off_hand": "dagger_off"},
                },
                class_features={"features": [], "runtime": {}},
                race_features={},
            )
        }

        sync_pcs_from_chars(session_id, chars_by_uid)

        state = get_combat(session_id)
        assert state is not None
        combatant = state.combatants["pc_1"]
        assert combatant.inventory == chars_by_uid[1].stats["_inv"]
        assert combatant.equip == chars_by_uid[1].stats["_equip"]
    finally:
        end_combat(session_id)
