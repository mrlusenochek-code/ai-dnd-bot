def class_hit_die(class_kit: str, class_skin: str) -> int:
    from app.rules.character_catalog import class_hit_die_by_catalog

    return class_hit_die_by_catalog(class_kit, class_skin)
