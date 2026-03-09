from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def test_lizardfolk_cunning_artisan_craft_darts_rolls_1d4_and_updates_inventory() -> None:
    ch = SimpleNamespace(
        stats={},
        race_features={"features": {"cunning_artisan": {"during": "short_rest"}}},
    )

    msg, err, changed = ws_handlers._apply_lizardfolk_cunning_artisan_craft(ch, "darts", rng=_FixedRng(3))
    assert err is None
    assert changed is True
    assert isinstance(msg, str) and "создано" in msg.lower()
    assert "3" in msg

    inv = (ch.stats or {}).get("_inv") or []
    dart = next((x for x in inv if str((x or {}).get("def") or "").strip().lower() == "dart"), {})
    assert int(dart.get("qty") or 0) == 3


def test_lizardfolk_cunning_artisan_rejects_for_non_lizardfolk() -> None:
    ch = SimpleNamespace(stats={}, race_features={"features": {}})
    msg, err, changed = ws_handlers._apply_lizardfolk_cunning_artisan_craft(ch, "darts", rng=_FixedRng(2))
    assert msg is None
    assert changed is False
    assert isinstance(err, str) and "недоступен" in err.lower()
