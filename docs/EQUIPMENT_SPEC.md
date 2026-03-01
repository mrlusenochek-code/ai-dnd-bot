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
- `wear_group: str | None = None` — логическая группа экипировки (`armor`, `shield`, `weapon` и т.д.).
- `paired: bool = False` — парный предмет (например, набор из двух предметов).
- `requires_attunement: bool = False` — требуется настройка/attunement.
- `weapon: WeaponStats | None = None` — боевые характеристики оружия.
- `dex_cap: int | None = None` — верхний предел бонуса Ловкости к AC (обычно для средней брони).
- `str_req: int | None = None` — минимальное требование Силы для ношения/эффективного использования.
- `stealth_disadvantage: bool = False` — помеха на проверки Скрытности.
- `notes: str | None = None` — служебная заметка.

Практические правила:

- `base_ac` использовать только для брони (`kind=armor`).
- `grants_ac_bonus` обычно для щитов и спец-предметов.
- `two_handed=True` ставить только для оружия, требующего обе руки.
- `weapon` заполнять только для предметов оружия (`kind=weapon`).

## WeaponStats

Структура для боевых параметров оружия, вложенная в `EquipSpec.weapon`.

Обязательные поля:

- `damage_dice: str` — кубы урона (пример: `1d8`).
- `damage_type: str` — тип урона (`slashing`, `piercing`, `bludgeoning` и т.д.).

Опциональные поля:

- `properties: tuple[str, ...] = ()` — свойства оружия (`finesse`, `light`, `thrown`, `versatile`, `ammunition`, `two-handed`).
- `range_normal: int | None = None` — нормальная дальность (для дальнобойного/метательного оружия).
- `range_long: int | None = None` — максимальная дальность с помехой.
- `versatile_dice: str | None = None` — альтернативные кубы урона при использовании свойства `versatile`.
- `mastery: str | None = None` — тип Weapon Mastery (например, `nick`, `sap`, `vex`).

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
