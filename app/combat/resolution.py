from dataclasses import dataclass


@dataclass(frozen=True)
class AttackResolution:
    d20_roll: int
    attack_bonus: int
    target_ac: int
    total_to_hit: int
    is_hit: bool
    is_crit: bool
    damage_roll: int
    damage_bonus: int
    total_damage: int


def resolve_attack_roll(
    *,
    d20_roll: int,
    attack_bonus: int,
    target_ac: int,
    damage_roll: int,
    damage_bonus: int = 0,
) -> AttackResolution:
    if not 1 <= d20_roll <= 20:
        raise ValueError("d20_roll must be in range [1, 20]")
    if target_ac < 0:
        raise ValueError("target_ac must be >= 0")
    if damage_roll < 0:
        raise ValueError("damage_roll must be >= 0")

    total_to_hit = d20_roll + attack_bonus
    is_crit = d20_roll == 20
    is_hit = is_crit or (d20_roll != 1 and total_to_hit >= target_ac)

    if not is_hit:
        total_damage = 0
    else:
        roll_damage = damage_roll * 2 if is_crit else damage_roll
        total_damage = max(0, roll_damage + damage_bonus)

    return AttackResolution(
        d20_roll=d20_roll,
        attack_bonus=attack_bonus,
        target_ac=target_ac,
        total_to_hit=total_to_hit,
        is_hit=is_hit,
        is_crit=is_crit,
        damage_roll=damage_roll,
        damage_bonus=damage_bonus,
        total_damage=total_damage,
    )
