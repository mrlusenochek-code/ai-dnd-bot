from __future__ import annotations


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def ability_score_from_stat100(stat: int) -> int:
    """
    Маппинг текущей шкалы 0..100 -> PHB ability score 3..20.
    Простой и предсказуемый: 50 -> 10, 100 -> 20.
    """
    s = _clamp(int(stat), 0, 100)
    score = int(round(s / 5.0))
    return _clamp(score, 3, 20)


def ability_mod_from_score(score: int) -> int:
    # PHB: (score - 10) // 2
    return (int(score) - 10) // 2


def ability_mod_from_stat100(stat: int) -> int:
    return ability_mod_from_score(ability_score_from_stat100(stat))


def proficiency_bonus(level: int) -> int:
    # PHB: 1–4:+2, 5–8:+3, 9–12:+4, 13–16:+5, 17–20:+6
    lvl = max(1, int(level))
    return _clamp(2 + (lvl - 1) // 4, 2, 6)