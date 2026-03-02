from app.gm import checks


def test_extract_checks_flags_skill_check_placeholder_noise() -> None:
    draft = "Сцена замирает.\nПРОВЕРКА_НАВЫКОВ\nЧто делаете дальше?"
    text, found, has_human = checks._extract_checks_from_draft(draft, default_actor_uid=3)
    assert text == draft
    assert found == []
    assert has_human is True


def test_extract_checks_flags_template_noise_with_dc() -> None:
    draft = "Шаблон:\n@.-check_template dc 15\nПродолжай сцену."
    _text, found, has_human = checks._extract_checks_from_draft(draft, default_actor_uid=None)
    assert found == []
    assert has_human is True


def test_extract_checks_keeps_clean_text_without_noise() -> None:
    draft = "Ты осматриваешь комнату и прислушиваешься к шагам за дверью."
    _text, found, has_human = checks._extract_checks_from_draft(draft, default_actor_uid=1)
    assert found == []
    assert has_human is False
