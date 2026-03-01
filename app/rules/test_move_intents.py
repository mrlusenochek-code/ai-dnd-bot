from app.rules.move_intents import parse_move_intent


def test_parse_move_intent_basic_words():
    assert parse_move_intent("вперед").dir == "n"
    assert parse_move_intent("назад").dir == "s"
    assert parse_move_intent("налево").dir == "w"
    assert parse_move_intent("направо").dir == "e"
    assert parse_move_intent("север").dir == "n"
    assert parse_move_intent("юг").dir == "s"
    assert parse_move_intent("восток").dir == "e"
    assert parse_move_intent("запад").dir == "w"


def test_parse_move_intent_verb_phrases():
    assert parse_move_intent("иду вперед").dir == "n"
    assert parse_move_intent("идём на север").dir == "n"
    assert parse_move_intent("двигаюсь на юг").dir == "s"
    assert parse_move_intent("пойду налево").dir == "w"
    assert parse_move_intent("шагаю направо!").dir == "e"


def test_parse_move_intent_not_move():
    assert parse_move_intent("смотрю вперед") is None
    assert parse_move_intent("иду искать трактир") is None
    assert parse_move_intent("") is None
