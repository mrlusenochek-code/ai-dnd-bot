# SRD Equipment Notes

Краткие заметки по SRD/5e-логике ношения предметов и как это приземлить в нашу модель слотов.

## 1) Wearing / Wielding (SRD)

- Обычно можно носить только:
- `1` головной предмет (headwear).
- `1` плащ/накидку (cloak).
- `1` пару обуви (boots).
- `1` пару перчаток/рукавиц (gloves/gauntlets).
- `1` щит (shield).
- `1` комплект доспеха (armor suit).
- Оружие: можно держать в руках по правилам слотов рук; двуручное оружие занимает обе руки.

## 2) Multiple Items Of Same Kind

- Предметы одного и того же "носимого типа" обычно не носятся одновременно (например, два плаща).
- Эффекты магических предметов не должны безусловно стакаться по принципу "чем больше, тем лучше"; если эффект одинакового имени/типа, обычно применяем один.
- В движке это лучше валидировать через группу ношения (`wear_group`) и правила стака эффектов.

## 3) Paired Items

- Некоторые предметы по смыслу парные и занимают "пару" как один wear-slot:
- обувь (левая+правая),
- перчатки (левая+правая),
- рукавицы/наручи как комплект.
- Для каталога нужен флаг `paired`, чтобы не пытаться экипировать половину пары.

## 4) Attunement

- Лимит attunement: `3` предмета на персонажа.
- Attunement требуется только для части магических предметов.
- Если предмет требует attunement, его магические свойства активны только после успешной attune-процедуры.
- Валидация: нельзя attune 4-й предмет, пока не разорвана attunement-связь с одним из текущих.

## 5) AC Base Formula: "Choose One"

- Базовый AC считается по **одной** формуле за раз (например, броня ИЛИ unarmored defense ИЛИ natural armor).
- Эти базовые формулы между собой не суммируются.
- После выбора базы отдельно добавляются модификаторы-надбавки (например, щит `+2`, ситуативные бонусы).

## 6) Mapping To Our Slots

- `headwear` -> `EquipmentSlot.head`
- `cloak` -> `EquipmentSlot.back`
- `boots` -> `EquipmentSlot.feet`
- `gloves/gauntlets` -> `EquipmentSlot.hands`
- `bracers` -> `EquipmentSlot.wrists`
- `armor suit` -> `EquipmentSlot.body`
- `shield` -> `EquipmentSlot.off_hand`
- `weapon (melee)` -> `EquipmentSlot.main_hand` или `EquipmentSlot.off_hand`
- `weapon (two-handed)` -> `EquipmentSlot.main_hand` + `EquipmentSlot.off_hand` (через `two_handed=True`)
- `weapon (ranged ready slot)` -> `EquipmentSlot.ranged`
- `ring` -> `EquipmentSlot.ring_left` / `EquipmentSlot.ring_right`

## 7) EquipSpec Metadata To Add Next

Предлагаемые поля для следующей итерации `EquipSpec`:

- `wear_group: str | None` — логическая группа взаимоисключения (например: `headwear`, `cloak`, `boots`, `gloves`, `shield`, `armor`).
- `paired: bool = False` — предмет является парным комплектом.
- `requires_attunement: bool = False` — нужен ли attunement.
- `weapon_stats: WeaponStats | None` — профиль оружия (тип урона, кость урона, свойства weapon tags).
- `armor_reqs: ArmorRequirements | None` — требования/ограничения брони (мин. STR, стелс-помеха, владение).

Минимальная идея для AC:

- хранить источник базовой формулы AC отдельно от бонусов,
- и валидировать, что активен только один base-источник одновременно.
