from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _rogue_with_slippery_mind(*, level: int = 15) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
        stats={"wis": 70, "dex": 70, "cha": 70},
        class_features=(
            {
                "features": [
                    {
                        "key": "slippery_mind",
                        "mechanics": {
                            "type": "saving_throw_proficiency",
                            "ability": "wis",
                            "source": "slippery_mind",
                        },
                    }
                ],
                "runtime": {},
            }
            if level >= 15
            else {"features": [], "runtime": {}}
        ),
    )


def test_manual_wis_save_gets_slippery_mind_proficiency_bonus() -> None:
    rogue = _rogue_with_slippery_mind(level=15)
    assert ws_handlers._effective_saving_throw_mod(rogue, "wis") == 7


def test_manual_dex_and_cha_saves_do_not_get_slippery_mind_bonus() -> None:
    rogue = _rogue_with_slippery_mind(level=15)
    assert ws_handlers._effective_saving_throw_mod(rogue, "dex") == 2
    assert ws_handlers._effective_saving_throw_mod(rogue, "cha") == 2
