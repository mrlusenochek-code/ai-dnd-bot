from app.gm import checks
from app.web import server


def test_extract_checks_from_draft_wrapper_equals_module() -> None:
    draft = (
        "Сцена продолжается.\n"
        "@@CHECK {\"actor_uid\":null,\"kind\":\"skill\",\"name\":\"perception\",\"dc\":14,\"mode\":\"normal\"}\n"
        "Что делаете дальше?"
    )
    expected = checks._extract_checks_from_draft(draft, default_actor_uid=7)
    actual = server._extract_checks_from_draft(draft, default_actor_uid=7)
    assert actual == expected
    text, found, has_human = actual
    assert text == "Сцена продолжается.\nЧто делаете дальше?"
    assert has_human is False
    assert found == [{"actor_uid": 7, "kind": "skill", "name": "perception", "dc": 14, "mode": "normal"}]


def test_checks_from_human_text_wrapper_equals_module() -> None:
    text = "Проверка: perception DC 15. Потом двигаюсь дальше."
    expected = checks._checks_from_human_text(text, default_actor_uid=11)
    actual = server._checks_from_human_text(text, default_actor_uid=11)
    assert actual == expected
    assert actual == [
        {
            "actor_uid": 11,
            "kind": "skill",
            "name": "perception",
            "dc": 15,
            "mode": "normal",
            "reason": "ранее запрошено текстом",
        }
    ]


def test_mandatory_category_cases() -> None:
    theft = "Пробую украсть кошелек у торговца"
    mechanics = "Пытаюсь взломать замок, в итоге вскрыл дверь"
    stealth = "Пытаюсь проскользнуть мимо стражи"
    assert server._mandatory_check_category(theft) == checks._mandatory_check_category(theft) == "theft"
    assert server._mandatory_check_category(mechanics) == checks._mandatory_check_category(mechanics) == "mechanics"
    assert server._mandatory_check_category(stealth) == checks._mandatory_check_category(stealth) == "stealth"


def test_mandatory_check_category_stealth_sneak_and_eavesdrop() -> None:
    text = "пытаюсь тихо подкрасться и подслушать"
    assert checks._mandatory_check_category(text) == "stealth"


def test_mandatory_check_category_stealth_leave_quietly() -> None:
    text = "пытаюсь скрытно уйти"
    assert checks._mandatory_check_category(text) == "stealth"


def test_mandatory_check_category_talking_quietly_is_not_stealth() -> None:
    text = "тихо разговариваю со стражником"
    assert checks._mandatory_check_category(text) != "stealth"


def test_autogen_check_for_category_wrapper_equals_module() -> None:
    text = "Пробую взломать сложный механизм замка"
    expected = checks._autogen_check_for_category("mechanics", text, actor_uid=5)
    actual = server._autogen_check_for_category("mechanics", text, actor_uid=5)
    assert actual == expected
    assert actual == {
        "actor_uid": 5,
        "kind": "skill",
        "name": "crafting",
        "dc": 15,
        "mode": "normal",
        "reason": "auto:mechanics",
    }


def test_extract_last_context_line_wrapper_equals_module() -> None:
    prompt = (
        "Интро\n"
        "Контекст (последние события):\n"
        "- [SYSTEM] ход\n"
        "- 🧙 GM: мастер обрабатывает\n"
        "- Игрок: осматриваюсь вокруг\n"
    )
    expected = checks._extract_last_context_line_from_prompt(prompt)
    actual = server._extract_last_context_line_from_prompt(prompt)
    assert actual == expected == "Игрок: осматриваюсь вокруг"
