from __future__ import annotations

from types import SimpleNamespace

from app.rules.derived_stats import compute_ac
from app.web import ws_handlers


def _simic_character(*, level: int = 5, lvl1: str = "manta_glide"):
    return SimpleNamespace(
        level=level,
        race_features={
            "race_key": "simic_hybrid",
            "speeds": {"walk_ft": 30},
            "features": {
                "animal_enhancement": {
                    "pick_1_level": 1,
                    "pick_2_level": 5,
                    "chosen_lvl1": lvl1,
                    "chosen_lvl5": None,
                }
            },
            "choices": {"animal_enhancement_lvl1": lvl1},
            "runtime": {"simic_lvl1_enhancement": lvl1, "simic_lvl5_enhancement": "", "acid_spit_uses_used": 0},
        },
    )


def test_simic_level5_upgrade_carapace_applies_and_persists() -> None:
    ch = _simic_character()

    err, msg, changed = ws_handlers._apply_simic_level5_upgrade(ch, "carapace")
    assert err is None
    assert changed is True
    assert msg is not None and "Панцирь" in msg

    rf = ch.race_features or {}
    assert ((rf.get("features") or {}).get("animal_enhancement") or {}).get("chosen_lvl5") == "carapace"
    assert (rf.get("choices") or {}).get("animal_enhancement_lvl5") == "carapace"
    assert ((rf.get("features") or {}).get("ac_bonus_if_no_heavy_armor") or {}).get("ac_bonus") == 1
    assert compute_ac(stats={"dex": 50}, inventory=[], equip_map={}, race_features=rf) == 11


def test_simic_level5_upgrade_acid_spit_available_and_level_gated() -> None:
    ch = _simic_character(lvl1="nimble_climber")

    err, _msg, changed = ws_handlers._apply_simic_level5_upgrade(ch, "acid_spit")
    assert err is None
    assert changed is True
    acid = ((ch.race_features or {}).get("features") or {}).get("acid_spit") or {}
    assert int(acid.get("range_ft") or 0) == 30
    assert str(acid.get("uses_formula") or "").strip().lower() == "max(con_mod,1)"
    assert int(((ch.race_features or {}).get("runtime") or {}).get("acid_spit_uses_used") or 0) == 0

    low_level = _simic_character(level=4)
    err_low, _msg_low, changed_low = ws_handlers._apply_simic_level5_upgrade(low_level, "acid_spit")
    assert changed_low is False
    assert err_low is not None and "5 уровня" in err_low
