\# PHB Truth (RAW math baseline)



Этот документ фиксирует “истину” базовой математики игрока по Player’s Handbook (PHB).

В проекте статы \*\*хранятся\*\* как 0..100, но все проверки/AC/атаки используют \*\*RAW-слой\*\*.



\## 1) Статы (0..100) → Ability Score (3..20)

Источник: `app/rules/phb\_math.py`



\- Храним: `stat100` в диапазоне 0..100 (обычно 50 = “средний”)

\- Перевод:

&nbsp; - `score = clamp(round(stat100 / 5), 3, 20)`

&nbsp; - Пример: 50 → 10, 70 → 14, 90 → 18, 100 → 20



\## 2) Ability Modifier (PHB)

Источник: `app/rules/phb\_math.py`



\- `mod = (score - 10) // 2`

\- Примеры:

&nbsp; - score 10 → +0

&nbsp; - score 14 → +2

&nbsp; - score 18 → +4

&nbsp; - score 3 → -4

&nbsp; - score 20 → +5



\## 3) Proficiency Bonus (PHB)

Источник: `app/rules/phb\_math.py`



\- Уровни:

&nbsp; - 1–4: +2

&nbsp; - 5–8: +3

&nbsp; - 9–12: +4

&nbsp; - 13–16: +5

&nbsp; - 17–20: +6



\## 4) Armor Class (PHB)

Источник: `app/rules/derived\_stats.py::compute\_ac`



\- Без брони: `AC = 10 + DEX\_mod`

\- Лёгкая броня: `base\_ac + DEX\_mod`

\- Средняя броня: `base\_ac + min(DEX\_mod, dex\_cap)` (обычно cap = 2)

\- Тяжёлая броня: `base\_ac` (DEX не добавляется)

\- Щит: `+ grants\_ac\_bonus` (обычно +2)



Примечание: параметры брони/щитов берутся из `app/rules/item\_catalog.py`.



\## 5) Проверки навыков/характеристик (PHB)

Источники:

\- `app/web/ws\_checks.py`

\- `app/web/ws\_handlers.py` (ручные вычисления модов)



\- Бонус проверки:

&nbsp; - `total\_mod = ability\_mod + proficiency\_bonus` (если владение)

&nbsp; - В проекте “compat” слой для legacy навыков:

&nbsp;   - `Skill.rank < 1` → не владеет → +0

&nbsp;   - `rank 1..3` → владеет → +prof

&nbsp;   - `rank >= 4` → expertise → +2\*prof

&nbsp; - Proficiency считается по `character.level`.



\## 6) Атака и урон (PHB)

Источники:

\- `app/rules/derived\_stats.py::compute\_attack\_profile`

\- `app/combat/live\_actions.py` (использует AttackProfile)



\- Выбор модификатора оружия (MVP):

&nbsp; - ranged/ammunition → DEX\_mod

&nbsp; - finesse → max(STR\_mod, DEX\_mod)

&nbsp; - иначе → STR\_mod



\- Бонус атаки:

&nbsp; - `attack\_bonus = ability\_mod + proficiency\_bonus(level)`

&nbsp; - (в MVP считаем, что владение оружием есть)



\- Бонус урона:

&nbsp; - `damage\_bonus = ability\_mod`



\## 7) Инициатива (PHB)

Источники:

\- `app/rules/phb\_math.py::roll\_initiative`

\- Web-команда: `app/web/ws\_handlers.py` → `init roll`



\- `initiative = d20 + DEX\_mod`



\## 8) Боёвка: протяжка уровня

Источники:

\- `app/combat/state.py` (`Combatant.level`)

\- `app/combat/sync\_pcs.py` (передаёт level из Character)

\- `app/combat/live\_actions.py` (передаёт level в compute\_attack\_profile)



\## 9) Принцип изменений

\- Любые изменения математики должны сопровождаться unit-тестами.

\- E2E smoke (`app/web/test\_e2e\_player\_journey\_smoke.py`) не должен ломаться.

