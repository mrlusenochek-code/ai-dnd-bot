from app.rules.class_progression import sync_class_features_for_level


def test_sync_class_features_for_level_unlocks_features_up_to_current_level() -> None:
    class_features = {
        "class_key": "fighter",
        "features_by_level": {
            1: [
                {
                    "key": "fighting_style",
                    "name_ru": "Боевой стиль",
                    "summary_ru": "Вы выбираете боевой стиль.",
                    "mechanics": {},
                }
            ],
            2: [
                {
                    "key": "action_surge",
                    "name_ru": "Всплеск действий",
                    "summary_ru": "Вы получаете дополнительное действие.",
                    "mechanics": {},
                }
            ],
            3: [
                {
                    "key": "martial_archetype",
                    "name_ru": "Воинский архетип",
                    "summary_ru": "Вы выбираете архетип.",
                    "mechanics": {"type": "subclass_choice"},
                }
            ],
            5: [
                {
                    "key": "extra_attack",
                    "name_ru": "Дополнительная атака",
                    "summary_ru": "Вы можете атаковать дважды.",
                    "mechanics": {},
                }
            ],
        },
        "subclass": {"key": "champion", "name_ru": "Чемпион"},
    }

    synced = sync_class_features_for_level(class_features, 3)

    assert synced["class_key"] == "fighter"
    assert synced["subclass"] == {"key": "champion", "name_ru": "Чемпион"}

    feature_keys = [item["key"] for item in synced["features"]]
    assert feature_keys == ["fighting_style", "action_surge"]


def test_sync_class_features_for_level_unlocks_later_features_after_level_up() -> None:
    class_features = {
        "class_key": "fighter",
        "features_by_level": {
            "1": [{"key": "fighting_style", "name_ru": "Боевой стиль"}],
            "5": [{"key": "extra_attack", "name_ru": "Дополнительная атака"}],
        },
    }

    synced = sync_class_features_for_level(class_features, 5)

    feature_keys = [item["key"] for item in synced["features"]]
    assert feature_keys == ["fighting_style", "extra_attack"]
