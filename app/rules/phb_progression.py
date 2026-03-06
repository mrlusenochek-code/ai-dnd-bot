def _norm(value: str) -> str:
    return str(value or "").strip().lower()


def class_hit_die(class_kit: str, class_skin: str) -> int:
    by_class = {
        "fighter": 10,
        "rogue": 8,
        "ranger": 10,
        "mage": 6,
        "cleric": 8,
        "bard": 8,
    }
    kit = _norm(class_kit)
    if kit in by_class:
        return by_class[kit]
    skin = _norm(class_skin)
    if skin in by_class:
        return by_class[skin]
    return 8
