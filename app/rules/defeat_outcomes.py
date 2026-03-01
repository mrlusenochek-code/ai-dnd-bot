from __future__ import annotations

import random
import zlib
from dataclasses import dataclass


@dataclass(frozen=True)
class DefeatOutcome:
    key: str
    title_ru: str
    description_ru: str
    weight: int = 1
    tags: tuple[str, ...] = ()


DEFAULT_DEFEAT_OUTCOMES: tuple[DefeatOutcome, ...] = (
    DefeatOutcome(
        key="captured",
        title_ru="Плен",
        description_ru="Героя обезоружили и взяли в плен.\nЕсть шанс выбраться позже.",
        weight=3,
        tags=("control", "story_hook"),
    ),
    DefeatOutcome(
        key="robbed",
        title_ru="Ограбление",
        description_ru="Противники забрали ценности и снаряжение.\nПерсонаж остаётся в живых.",
        weight=2,
        tags=("loss",),
    ),
    DefeatOutcome(
        key="enemies_withdraw",
        title_ru="Враг отступил",
        description_ru="Враги сочли бой законченным и ушли.\nПерсонаж приходит в себя позже.",
        weight=2,
        tags=("survival",),
    ),
    DefeatOutcome(
        key="rescued",
        title_ru="Спасён",
        description_ru="Союзник или случайный путник спасает героя.\nЦена спасения выяснится позже.",
        weight=1,
        tags=("aid", "story_hook"),
    ),
    DefeatOutcome(
        key="left_for_dead",
        title_ru="Брошен умирать",
        description_ru="Героя оставили без помощи.\nОн выживает чудом и нуждается в восстановлении.",
        weight=1,
        tags=("grim", "survival"),
    ),
)


def pick_defeat_outcome(
    *, started_at_iso: str, rng: random.Random | None = None
) -> DefeatOutcome:
    random_source = rng
    if random_source is None:
        seed = zlib.adler32(started_at_iso.encode("utf-8")) & 0xFFFFFFFF
        random_source = random.Random(seed)

    total_weight = sum(outcome.weight for outcome in DEFAULT_DEFEAT_OUTCOMES)
    roll = random_source.randint(1, total_weight)

    threshold = 0
    for outcome in DEFAULT_DEFEAT_OUTCOMES:
        threshold += outcome.weight
        if roll <= threshold:
            return outcome

    return DEFAULT_DEFEAT_OUTCOMES[-1]
