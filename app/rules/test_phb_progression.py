from app.rules.phb_progression import class_hit_die


def test_class_hit_die_known_classes() -> None:
    assert class_hit_die("fighter", "") == 10
    assert class_hit_die("mage", "") == 6
    assert class_hit_die("rogue", "") == 8
    assert class_hit_die("unknown", "") == 8


def test_class_hit_die_fallbacks_to_class_skin() -> None:
    assert class_hit_die("  weird_kit  ", "  ranger  ") == 10
