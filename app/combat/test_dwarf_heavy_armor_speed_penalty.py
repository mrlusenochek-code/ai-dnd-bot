from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.combat.sync_pcs import sync_pcs_from_chars


def test_sync_pcs_applies_heavy_armor_speed_penalty_with_dwarf_exception(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    heavy_inv = [{"id": "armor1", "def": "chain_mail"}]
    heavy_equip = {"body": "armor1"}
    base_stats = {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50}

    chars_by_uid = {
        1: SimpleNamespace(
            name="NoMarker",
            hp=10,
            hp_max=10,
            level=1,
            speed_ft=25,
            stats={**base_stats, "_inv": heavy_inv, "_equip": heavy_equip},
            race_features={},
        ),
        2: SimpleNamespace(
            name="Dwarf",
            hp=10,
            hp_max=10,
            level=1,
            speed_ft=25,
            stats={**base_stats, "_inv": heavy_inv, "_equip": heavy_equip},
            race_features={"movement": {"ignore_heavy_armor_speed_penalty": True}},
        ),
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    by_key = {str(c.get("pc_key") or ""): c for c in calls}
    non_dwarf = by_key["pc_1"]
    dwarf = by_key["pc_2"]

    assert non_dwarf["speed_ft"] == 15
    assert int((non_dwarf.get("movement_speeds") or {}).get("walk") or 0) == 15

    assert dwarf["speed_ft"] == 25
    assert int((dwarf.get("movement_speeds") or {}).get("walk") or 0) == 25


def test_sync_pcs_speed_override_bypasses_heavy_armor_penalty(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    heavy_inv = [{"id": "armor1", "def": "chain_mail"}]
    heavy_equip = {"body": "armor1"}

    chars_by_uid = {
        3: SimpleNamespace(
            name="Override",
            hp=10,
            hp_max=10,
            level=1,
            speed_ft=25,
            stats={
                "str": 50,
                "dex": 50,
                "con": 50,
                "int": 50,
                "wis": 50,
                "cha": 50,
                "_inv": heavy_inv,
                "_equip": heavy_equip,
            },
            race_features={"runtime": {"speed_override_ft": 40}},
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["speed_ft"] == 40
    assert calls[0]["movement_speeds"] == {"walk": 40, "swim": 40, "climb": 40, "fly": 40}
