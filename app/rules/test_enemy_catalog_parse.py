from app.rules.enemy_catalog import parse_enemy_html


OREAD_HTML = """
<div class='card__header'>
  <h2 class="card-title" itemprop="name">
    <span data-copy="Ореада [Oread]">Ореада [Oread]</span>
  </h2>
</div>
<ul class="params card__article-body">
  <li><strong>Класс Доспеха</strong> 16 (природный доспех)</li>
  <li><strong>Хиты</strong> <span data-type='middle'>49</span> (<span data-type='throw'>9</span>к<span data-type='dice'>8</span> + <span data-type='bonus'>9</span>)</li>
  <li class='abilities'>
    <div class='stat' title='Сила'><div>Сил</div><div>14 (<strong>+2</strong>)</div></div>
    <div class='stat' title='Ловкость'><div>Лов</div><div>14 (<strong>+2</strong>)</div></div>
    <div class='stat' title='Телосложение'><div>Тел</div><div>12 (<strong>+1</strong>)</div></div>
    <div class='stat' title='Интеллект'><div>Инт</div><div>11 (<strong>+0</strong>)</div></div>
    <div class='stat' title='Мудрость'><div>Мдр</div><div>13 (<strong>+1</strong>)</div></div>
    <div class='stat' title='Харизма'><div>Хар</div><div>18 (<strong>+4</strong>)</div></div>
  </li>
  <li><strong>Опасность</strong> 4 (1100 опыта)</li>
</ul>
"""


GIANT_BOAR_HTML = """
<div class='card__header'>
  <h2 class="card-title" itemprop="name">
    <span data-copy="Гигантский кабан [Giant boar]">Гигантский кабан [Giant boar]</span>
  </h2>
</div>
<ul class="params card__article-body">
  <li><strong>Класс Доспеха</strong> 12 (природный доспех)</li>
  <li><strong>Хиты</strong> <span data-type='middle'>42</span> (<span data-type='throw'>5</span>к<span data-type='dice'>10</span> + <span data-type='bonus'>15</span>)</li>
  <li class='abilities'>
    <div class='stat' title='Сила'><div>Сил</div><div>17 (<strong>+3</strong>)</div></div>
    <div class='stat' title='Ловкость'><div>Лов</div><div>10 (<strong>+0</strong>)</div></div>
    <div class='stat' title='Телосложение'><div>Тел</div><div>16 (<strong>+3</strong>)</div></div>
    <div class='stat' title='Интеллект'><div>Инт</div><div>2 (<strong>-4</strong>)</div></div>
    <div class='stat' title='Мудрость'><div>Мдр</div><div>7 (<strong>-2</strong>)</div></div>
    <div class='stat' title='Харизма'><div>Хар</div><div>5 (<strong>-3</strong>)</div></div>
  </li>
  <li><strong>Опасность</strong> 2 (450 опыта)</li>
  <li><strong>Местность обитания</strong> лес, луг, холмы</li>
</ul>
"""


def test_parse_enemy_html_without_environments() -> None:
    enemy = parse_enemy_html(OREAD_HTML, key_hint="dndsu_7163_oread")

    assert enemy.key == "dndsu_7163_oread"
    assert enemy.name_ru == "Ореада"
    assert enemy.name_en == "Oread"
    assert enemy.ac == 16
    assert enemy.hp_avg == 49
    assert enemy.hp_formula == "9d8 + 9"
    assert enemy.cr == "4"
    assert enemy.xp == 1100
    assert enemy.stats == {
        "str": 14,
        "dex": 14,
        "con": 12,
        "int": 11,
        "wis": 13,
        "cha": 18,
    }
    assert enemy.environments == []


def test_parse_enemy_html_with_environments() -> None:
    enemy = parse_enemy_html(GIANT_BOAR_HTML, key_hint="dndsu_349_giant_boar")

    assert enemy.key == "dndsu_349_giant_boar"
    assert enemy.name_ru == "Гигантский кабан"
    assert enemy.name_en == "Giant boar"
    assert enemy.ac == 12
    assert enemy.hp_avg == 42
    assert enemy.hp_formula == "5d10 + 15"
    assert enemy.cr == "2"
    assert enemy.xp == 450
    assert enemy.stats == {
        "str": 17,
        "dex": 10,
        "con": 16,
        "int": 2,
        "wis": 7,
        "cha": 5,
    }
    assert enemy.environments == ["лес", "луг", "холмы"]
