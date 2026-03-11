from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, value: int) -> None:
        self._value = value

    def randint(self, _a: int, _b: int) -> int:
        return self._value


def _harengon_character(*, speed_override_ft=None, prone: bool = False) -> SimpleNamespace:
    runtime: dict[str, object] = {}
    if speed_override_ft is not None:
        runtime["speed_override_ft"] = speed_override_ft
    if prone:
        runtime["conditions"] = {"prone": {"active": True}}
    return SimpleNamespace(
        race_features={
            "speeds": {"walk_ft": 30},
            "features": {
                "lucky_footwork": {
                    "type": "failed_dex_save_bonus",
                    "dice": "1d4",
                    "trigger": "failed_dex_save",
                    "requires": {"not_prone": True, "speed_gt_0": True},
                }
            },
            "runtime": runtime,
        }
    )


def test_harengon_lucky_footwork_applies_only_after_failed_dex_save() -> None:
    ch = _harengon_character()

    bonus, bonus_text, note, changed, err = ws_handlers._consume_harengon_lucky_footwork_for_save(
        ch,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="dex",
        base_total=11,
        dc=15,
        rng=_FixedRng(4),
    )
    assert err is None
    assert changed is True
    assert bonus == 4
    assert bonus_text == "1d4(4)"
    assert note == ""

    runtime = (ch.race_features or {}).get("runtime") or {}
    result = runtime.get("last_dex_save_result") or {}
    assert int(result.get("new_total") or 0) == 15
    assert result.get("success") is True

    ch_success = _harengon_character()
    bonus2, bonus_text2, note2, changed2, err2 = ws_handlers._consume_harengon_lucky_footwork_for_save(
        ch_success,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="dex",
        base_total=16,
        dc=15,
        rng=_FixedRng(4),
    )
    assert err2 is None
    assert changed2 is False
    assert bonus2 == 0
    assert bonus_text2 == ""
    assert note2 == "Lucky Footwork не понадобилась."


def test_harengon_lucky_footwork_rejects_wrong_save_non_harengon_prone_and_speed_zero() -> None:
    ch = _harengon_character()
    _bonus, _bonus_text, _note, _changed, err = ws_handlers._consume_harengon_lucky_footwork_for_save(
        ch,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="wis",
        base_total=9,
        dc=15,
        rng=_FixedRng(3),
    )
    assert err is not None and "Ловкости" in err

    non_harengon = SimpleNamespace(race_features={"features": {}, "runtime": {}, "speeds": {"walk_ft": 30}})
    _bonus, _bonus_text, _note, _changed, err = ws_handlers._consume_harengon_lucky_footwork_for_save(
        non_harengon,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="dex",
        base_total=9,
        dc=15,
        rng=_FixedRng(3),
    )
    assert err is not None and "недоступны вашей расе" in err.lower()

    prone = _harengon_character(prone=True)
    _bonus, _bonus_text, _note, _changed, err = ws_handlers._consume_harengon_lucky_footwork_for_save(
        prone,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="dex",
        base_total=9,
        dc=15,
        rng=_FixedRng(3),
    )
    assert err is not None and "сбиты с ног" in err.lower()

    stopped = _harengon_character(speed_override_ft=0)
    _bonus, _bonus_text, _note, _changed, err = ws_handlers._consume_harengon_lucky_footwork_for_save(
        stopped,
        session_id="no-combat",
        player_uid=None,
        requested=True,
        ability="dex",
        base_total=9,
        dc=15,
        rng=_FixedRng(3),
    )
    assert err is not None and "скорость" in err.lower()
