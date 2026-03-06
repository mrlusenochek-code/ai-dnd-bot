from app.rules.phb_rest import apply_long_rest


def test_apply_long_rest_restores_to_max_values() -> None:
    assert apply_long_rest(hp=1, hp_max=10, sta=0, sta_max=7) == (10, 7)


def test_apply_long_rest_normalizes_hp_max_to_min_one() -> None:
    assert apply_long_rest(hp=5, hp_max=0, sta=3, sta_max=7) == (1, 7)


def test_apply_long_rest_normalizes_sta_max_to_min_zero() -> None:
    assert apply_long_rest(hp=5, hp_max=10, sta=3, sta_max=-5) == (10, 0)
