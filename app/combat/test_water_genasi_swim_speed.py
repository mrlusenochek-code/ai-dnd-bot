from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.combat.sync_pcs import sync_pcs_from_chars


def test_water_genasi_swim_speed_enters_shared_combat_movement(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    chars_by_uid = {
        1: SimpleNamespace(
            name="Water Genasi",
            hp=12,
            hp_max=12,
            level=1,
            speed_ft=30,
            stats={"dex": 50, "_inv": [], "_equip": {}},
            inventory=[],
            equip={},
            race_features={
                "speeds": {"walk_ft": 30, "swim_ft": 30},
                "breath": {"amphibious": True},
                "features": {"amphibious": True},
            },
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["speed_ft"] == 30
    assert calls[0]["movement_speeds"]["walk"] == 30
    assert calls[0]["movement_speeds"]["swim"] == 30


def test_non_water_genasi_does_not_get_swim_speed_in_shared_combat_movement(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_upsert_pc(session_id: str, **kwargs: Any) -> None:
        calls.append({"session_id": session_id, **kwargs})

    monkeypatch.setattr("app.combat.sync_pcs.upsert_pc", _fake_upsert_pc)

    chars_by_uid = {
        1: SimpleNamespace(
            name="Air Genasi",
            hp=12,
            hp_max=12,
            level=1,
            speed_ft=30,
            stats={"dex": 50, "_inv": [], "_equip": {}},
            inventory=[],
            equip={},
            race_features={"breath": {"hold": "unlimited"}},
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["movement_speeds"]["walk"] == 30
    assert "swim" not in calls[0]["movement_speeds"]
