from __future__ import annotations

from app.web import ws_handlers


class _FixedRng:
    def __init__(self, values: list[int]) -> None:
        self._values = list(values)
        self._idx = 0

    def randint(self, _a: int, _b: int) -> int:
        if self._idx >= len(self._values):
            return self._values[-1]
        value = self._values[self._idx]
        self._idx += 1
        return value


def test_verdan_rerolls_one_or_two_on_hit_dice_short_rest() -> None:
    race_features = {
        "features": {
            "hit_dice_reroll": {
                "when": "short_rest_spend_hit_dice",
                "reroll_on": [1, 2],
            }
        }
    }
    hp_before = 10
    hp_max = 30
    hit_die = 8
    hd_before = 1
    con_mod = 0
    rng = _FixedRng([2, 7])  # first roll rerolled to 7

    hp_after, hd_after, heals, reroll_logs = ws_handlers._apply_short_rest_spend_hd_with_racial_reroll(
        hp=hp_before,
        hp_max=hp_max,
        hit_die=hit_die,
        hit_dice_remaining=hd_before,
        con_mod=con_mod,
        spend=1,
        race_features=race_features,
        rng=rng,
    )

    assert hp_after == 17  # healed by 7, not by 2
    assert hd_after == 0
    assert heals == [7]
    assert any("Black Blood Healing" in line for line in reroll_logs)
    assert any("выпало 2 → 7" in line for line in reroll_logs)
