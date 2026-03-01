from app.rules.enemy_catalog_data import load_enemy_catalog, get_enemy, filter_enemies_by_env


def test_catalog_loads_and_indexes():
    cat = load_enemy_catalog()
    assert len(cat.enemies) > 1000
    assert len(cat.by_key) == len(cat.enemies)
    # из твоего head-фрагмента
    assert get_enemy("dndsu_1_twig_blight") is not None


def test_filter_by_env_city_not_empty():
    city = filter_enemies_by_env(["город"])
    assert len(city) > 0
