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
        )
    }

    sync_pcs_from_chars("s1", chars_by_uid)

    assert len(calls) == 1
    assert calls[0]["ac"] == 10
    assert calls[0]["speed_ft"] == 35
