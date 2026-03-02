from types import SimpleNamespace

from app.web import server


def test_skill_rank_equals_starter_and_zero_xp_hidden() -> None:
    skill = SimpleNamespace(skill_key="endurance", rank=1, xp=0)
    assert server._skill_is_active(skill, class_kit="fighter", class_skin="Fighter") is False


def test_skill_rank_non_starter_and_zero_xp_shown() -> None:
    skill = SimpleNamespace(skill_key="athletics", rank=1, xp=0)
    assert server._skill_is_active(skill, class_kit="rogue", class_skin="Rogue") is True


def test_skill_with_positive_xp_always_shown() -> None:
    skill = SimpleNamespace(skill_key="endurance", rank=1, xp=2)
    assert server._skill_is_active(skill, class_kit="fighter", class_skin="Fighter") is True
