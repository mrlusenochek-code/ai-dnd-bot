from types import SimpleNamespace

from app.rules.class_feature_runtime import (
    fighter_has_protection_style,
    fighter_has_two_weapon_fighting_style,
    has_fighting_style,
)
from app.rules.derived_stats import compute_ac, compute_attack_profile


def _fighter_class_features(choice) -> dict:
    return {
        "features": [
            {
                "key": "fighting_style",
                "mechanics": {
                    "type": "fighting_style",
                    "allowed_styles": [
                        "archery",
                        "defense",
                        "dueling",
                        "great_weapon_fighting",
                        "protection",
                        "two_weapon_fighting",
                    ],
                    "implemented_styles": ["archery", "defense", "dueling", "great_weapon_fighting", "protection", "two_weapon_fighting"],
                    "choice_key": "fighting_style",
                },
            }
        ],
        "choices": {"fighting_style": choice},
        "runtime": {},
    }


def test_defense_adds_plus_one_ac_in_armor() -> None:
    stats = {"dex": 50}
    inv = [{"id": "a1", "def": "chain_mail"}]
    equip_map = {"body": "a1"}
    assert compute_ac(stats=stats, inventory=inv, equip_map=equip_map, class_features=_fighter_class_features("defense")) == 17


def test_defense_does_not_add_plus_one_ac_without_armor() -> None:
    stats = {"dex": 50}
    assert compute_ac(stats=stats, inventory=[], equip_map={}, class_features=_fighter_class_features("defense")) == 10


def test_archery_adds_plus_two_attack_bonus_for_ranged_weapon() -> None:
    stats = {"str": 50, "dex": 50}
    inv = [{"id": "w1", "def": "shortbow"}]
    equip_map = {"ranged": "w1"}
    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1, class_features=_fighter_class_features("archery"))
    assert profile.attack_bonus == 4


def test_archery_does_not_bonus_melee_weapon() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}]
    equip_map = {"main_hand": "w1"}
    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1, class_features=_fighter_class_features("archery"))
    assert profile.attack_bonus == 6


def test_dueling_adds_plus_two_damage_for_one_handed_melee_weapon() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}]
    equip_map = {"main_hand": "w1"}
    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1, class_features=_fighter_class_features("dueling"))
    assert profile.damage_bonus == 6


def test_dueling_works_with_shield() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}, {"id": "s1", "def": "shield"}]
    equip_map = {"main_hand": "w1", "off_hand": "s1"}
    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1, class_features=_fighter_class_features({"key": "dueling"}))
    assert profile.damage_bonus == 6


def test_dueling_does_not_work_with_second_weapon_in_off_hand() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}, {"id": "w2", "def": "dagger"}]
    equip_map = {"main_hand": "w1", "off_hand": "w2"}
    profile = compute_attack_profile(stats=stats, inventory=inv, equip_map=equip_map, level=1, class_features=_fighter_class_features("dueling"))
    assert profile.damage_bonus == 4


def test_great_weapon_fighting_does_not_change_damage_bonus() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}]
    equip_map = {"main_hand": "w1"}
    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("great_weapon_fighting"),
    )
    assert profile.damage_bonus == 4


def test_great_weapon_fighting_profile_marks_true_two_handed_weapon() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "shortbow"}]
    equip_map = {"ranged": "w1"}
    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("great_weapon_fighting"),
    )
    assert profile.is_wielded_two_handed is True


def test_great_weapon_fighting_profile_requires_explicit_two_handed_versatile_use() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}]
    equip_map = {"main_hand": "w1"}
    profile_one_handed = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("great_weapon_fighting"),
    )
    assert profile_one_handed.is_wielded_two_handed is False

    inv_two_handed = [{"id": "w1", "def": "longsword", "wielded_two_handed": True}]
    profile_two_handed = compute_attack_profile(
        stats=stats,
        inventory=inv_two_handed,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("great_weapon_fighting"),
    )
    assert profile_two_handed.is_wielded_two_handed is True


def test_protection_style_helpers_detect_choice() -> None:
    ch = SimpleNamespace(class_features=_fighter_class_features("protection"))
    assert has_fighting_style(ch, "protection") is True
    assert fighter_has_protection_style(ch) is True


def test_protection_style_helper_false_without_style() -> None:
    ch = SimpleNamespace(class_features=_fighter_class_features("defense"))
    assert has_fighting_style(ch, "protection") is False
    assert fighter_has_protection_style(ch) is False


def test_two_weapon_fighting_style_helpers_detect_choice() -> None:
    ch = SimpleNamespace(class_features=_fighter_class_features("two_weapon_fighting"))
    assert has_fighting_style(ch, "two_weapon_fighting") is True
    assert fighter_has_two_weapon_fighting_style(ch) is True


def test_compute_attack_profile_weapon_slot_prefers_requested_offhand() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}, {"id": "w2", "def": "dagger"}]
    equip_map = {"main_hand": "w1", "off_hand": "w2"}
    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        weapon_slot="off_hand",
        level=1,
        class_features=_fighter_class_features("two_weapon_fighting"),
    )
    assert profile.damage_dice == "1d4"
    assert profile.weapon_slot == "off_hand"
    assert profile.is_light_weapon is True


def test_compute_attack_profile_default_still_prefers_main_hand() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}, {"id": "w2", "def": "dagger"}]
    equip_map = {"main_hand": "w1", "off_hand": "w2"}
    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("two_weapon_fighting"),
    )
    assert profile.damage_dice == "1d8"
    assert profile.weapon_slot == "main_hand"
    assert profile.is_light_weapon is False


def test_longsword_is_not_light_weapon() -> None:
    stats = {"str": 90, "dex": 50}
    inv = [{"id": "w1", "def": "longsword"}]
    equip_map = {"main_hand": "w1"}
    profile = compute_attack_profile(
        stats=stats,
        inventory=inv,
        equip_map=equip_map,
        level=1,
        class_features=_fighter_class_features("two_weapon_fighting"),
    )
    assert profile.is_light_weapon is False
