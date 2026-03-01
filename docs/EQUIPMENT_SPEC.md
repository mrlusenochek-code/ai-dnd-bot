# Equipment Item Schema

Документ описывает базовую схему предмета экипировки и инвентаря для каталога `app/rules/item_catalog.py`.

## Ключевые сущности

- `ItemDef` — основное описание предмета.
- `EquipSpec` — правила экипировки (если предмет можно надеть/взять в слот).

## ItemDef

Обязательные поля:

- `key: str` — стабильный идентификатор предмета в каталоге.
- `name_ru: str` — отображаемое название на русском.
- `kind: ItemKind` — тип предмета (`weapon`, `armor`, `shield`, `accessory`, `consumable`, `quest`, `misc`).

Опциональные поля:

- `stackable: bool = False` — можно ли складывать в один стек.
- `max_stack: int = 1` — максимальный размер стека.
- `equip: EquipSpec | None = None` — правила экипировки.
- `description_ru: str | None = None` — краткое описание.

Практические правила:

- Если `stackable=False`, оставлять `max_stack=1`.
- Если предмет экипируемый, должен быть заполнен `equip`.
- Для неэкипируемых предметов `equip=None`.

## EquipSpec

Обязательные поля:

- `allowed_slots: tuple[EquipmentSlot, ...]` — в какие слоты можно экипировать.

Опциональные поля:

- `two_handed: bool = False` — двуручное оружие.
- `armor_category: ArmorCategory | None = None` — категория брони (`light`, `medium`, `heavy`, `clothing`).
- `base_ac: int | None = None` — базовый AC для брони.
- `grants_ac_bonus: int = 0` — бонус к AC (например, от щита).
- `notes: str | None = None` — служебная заметка.

Практические правила:

- `base_ac` использовать только для брони (`kind=armor`).
- `grants_ac_bonus` обычно для щитов и спец-предметов.
- `two_handed=True` ставить только для оружия, требующего обе руки.

## Нейминг key

Формат:

- нижний регистр (lowercase)
- слова через underscore
- только латиница, цифры и `_`
- ключ должен быть стабильным и уникальным в `ITEMS`

Рекомендуемый шаблон:

- `<base_name>`: `leather_armor`, `dagger`, `shortbow`
- `<material>_<item>`: `iron_dagger`
- `<rarity_or_tag>_<item>`: `fine_longsword`

Нежелательно:

- пробелы, дефисы, кириллица в `key`
- временные суффиксы (`_new`, `_tmp`)
- переименование существующего `key` без миграции данных
