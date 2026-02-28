from __future__ import annotations

from typing import Any, Optional
import re


def extract_combat_narration_facts(patch: dict[str, Any] | None) -> list[str]:
    if not isinstance(patch, dict):
        return []
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return []
    attack_re = re.compile(r"^Атака:\s*(.+?)\s*→\s*(.+)\s*$", re.IGNORECASE)

    facts: list[str] = []
    pending: tuple[str, str] | None = None

    def clean_name(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "")).strip()

    for it in lines:
        text = None
        kind = None
        if isinstance(it, dict):
            text = it.get("text")
            kind = it.get("kind")
        elif isinstance(it, str):
            text = it
        if not isinstance(text, str):
            continue
        t = text.strip()
        if not t:
            continue

        # игнор служебного
        if t == "====================":
            continue
        if kind == "status" or t.startswith("⚔"):
            continue
        if t.startswith(("Бросок", "Урон:", "Ход автоматически")):
            continue
        if " vs AC " in t or "HP " in t:
            continue

        m = attack_re.match(t)
        if m:
            pending = (clean_name(m.group(1)), clean_name(m.group(2)))
            continue

        if pending and t.lower().startswith("результат:"):
            low = t.lower()
            outcome = "неясно"
            if "попадание" in low or "крит" in low:
                outcome = "попал"
            if "промах" in low:
                outcome = "промахнулся"
            facts.append(f"{pending[0]} атакует {pending[1]} и {outcome}.")
            pending = None
            continue

        low = t.lower()
        if "повержен" in low:
            facts.append("Противник повержен.")
            continue
        if low.startswith("победа"):
            facts.append("Победа — бой окончен.")
            continue
        if low.startswith("бой заверш"):
            facts.append("Бой завершён.")
            continue

    if pending:
        facts.append(f"{pending[0]} атакует {pending[1]}.")

    # ограничим размер
    facts = [f for f in facts if f]
    return facts[:10]
