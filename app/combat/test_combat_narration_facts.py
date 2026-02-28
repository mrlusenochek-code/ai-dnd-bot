import unittest

from app.combat.combat_narration_facts import extract_combat_narration_facts


def _patch(*lines: str) -> dict[str, object]:
    return {"lines": [{"text": line} for line in lines]}


class CombatNarrationFactsTests(unittest.TestCase):
    def test_parses_action_facts_in_russian_short_form(self) -> None:
        facts = extract_combat_narration_facts(
            _patch(
                "Уклонение: Разбойник (до следующего хода)",
                "Рывок: Воин (до следующего хода)",
                "Отход: Жрец (до следующего хода)",
                "Помощь: Маг (следующая атака с преимуществом)",
                "Предмет: Плут использует объект (до следующего хода)",
            )
        )

        self.assertEqual(
            facts,
            [
                "Разбойник уходит в защиту и сбивает темп.",
                "Воин резко ускоряется и меняет дистанцию.",
                "Жрец отступает, не подставляясь.",
                "Маг помогает, открывая окно для следующей атаки.",
                "Плут тянется к предмету и пытается использовать объект.",
            ],
        )

    def test_escape_result_fact_is_extracted(self) -> None:
        facts = extract_combat_narration_facts(
            _patch(
                "Побег: Разбойник пытается выйти из боя",
                "Результат: побег не удался",
            )
        )
        self.assertEqual(facts, ["Разбойник пытается уйти, но побег срывается."])

    def test_attack_outcome_and_hp_state_fact(self) -> None:
        facts = extract_combat_narration_facts(
            _patch(
                "Атака: Воин → Разбойник",
                "Результат: попадание",
                "Разбойник: HP 2/18",
            )
        )
        self.assertEqual(
            facts,
            [
                "Воин атакует Разбойник и попадает.",
                "Разбойник пошатывается и едва держится.",
            ],
        )

    def test_priority_outcomes_before_regular_buffs_and_fact_limit(self) -> None:
        facts = extract_combat_narration_facts(
            _patch(
                "Уклонение: А",
                "Рывок: Б",
                "Отход: В",
                "Помощь: Г",
                "Предмет: Д использует объект",
                "Победа: противники повержены.",
                "Е повержен.",
                "Бой завершён",
                "Поражение: все герои выбыли.",
                "Уклонение: Ж",
                "Рывок: З",
                "Отход: И",
            )
        )

        self.assertEqual(len(facts), 10)
        self.assertEqual(facts[0], "Победа — бой окончен.")
        self.assertEqual(facts[1], "Противник повержен.")
        self.assertEqual(facts[2], "Бой завершён.")
        self.assertEqual(facts[3], "Поражение — отряд выбывает.")


if __name__ == "__main__":
    unittest.main()