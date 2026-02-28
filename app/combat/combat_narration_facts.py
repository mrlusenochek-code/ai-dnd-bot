from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re


@dataclass
class _AttackPending:
    attacker: str
    target: str
    outcome_fact: str | None = None


def extract_combat_narration_facts(patch: dict[str, Any] | None) -> list[str]:
    if not isinstance(patch, dict):
        return []
    lines = patch.get("lines")
    if not isinstance(lines, list):
        return []

    attack_re = re.compile(r"^Атака:\s*(.+?)\s*→\s*(.+)\s*$", re.IGNORECASE)
    action_re = re.compile(r"^(Уклонение|Рывок|Отход|Помощь|Предмет|Побег):\s*(.+?)(?:\s*\(|\s*$)", re.IGNORECASE)
    hp_re = re.compile(r"^(.+?):\s*HP\s*(\d+)\s*/\s*(\d+)\s*$", re.IGNORECASE)

    facts_priority: list[str] = []
    facts_regular: list[str] = []
    pending_attack: _AttackPending | None = None
    pending_escape_actor: str | None = None

    def clean_name(s: Any) -> str:
        return re.sub(r"\s+", " ", str(s or "")).strip()

    def clean_actor(raw: Any) -> str:
        actor = clean_name(raw)
        for marker in (" пытается ", " использует "):
            idx = actor.lower().find(marker)
            if idx > 0:
                actor = actor[:idx].strip()
        return actor

    def add_priority(text: str) -> None:
        if text:
            facts_priority.append(text)

    def add_regular(text: str) -> None:
        if text:
            facts_regular.append(text)

    def hp_state_fact(name: str, hp_cur: int, hp_max: int) -> str | None:
        if hp_max <= 0:
            return None
        ratio = hp_cur / hp_max
        if ratio >= 0.75:
            return f"{name} почти не ранен."
        if ratio >= 0.40:
            return f"{name} ранен."
        if ratio >= 0.15:
            return f"{name} сильно ранен."
        return f"{name} пошатывается и едва держится."

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

        low = t.lower()

        # Игнор служебных или механических строк.
        if t == "====================":
            continue
        if kind == "status" or t.startswith("⚔"):
            continue
        if t.startswith(("Бросок", "Урон:", "Ход автоматически")):
            continue
        if " vs AC " in t:
            continue

        m_attack = attack_re.match(t)
        if m_attack:
            pending_attack = _AttackPending(
                attacker=clean_name(m_attack.group(1)),
                target=clean_name(m_attack.group(2)),
            )
            continue

        m_action = action_re.match(t)
        if m_action:
            action_kind = m_action.group(1).lower()
            actor = clean_actor(m_action.group(2))
            if not actor:
                continue
            if action_kind == "уклонение":
                add_regular(f"{actor} уходит в защиту и сбивает темп.")
            elif action_kind == "рывок":
                add_regular(f"{actor} резко ускоряется и меняет дистанцию.")
            elif action_kind == "отход":
                add_regular(f"{actor} отступает, не подставляясь.")
            elif action_kind == "помощь":
                add_regular(f"{actor} помогает, открывая окно для следующей атаки.")
            elif action_kind == "предмет":
                add_regular(f"{actor} тянется к предмету и пытается использовать объект.")
            elif action_kind == "побег":
                pending_escape_actor = actor
            continue

        if low.startswith("результат:"):
            if pending_attack:
                outcome = "не пробивает оборону"
                if "попадание" in low or "крит" in low:
                    outcome = "попадает"
                elif "промах" in low:
                    outcome = "промахивается"
                pending_attack.outcome_fact = f"{pending_attack.attacker} атакует {pending_attack.target} и {outcome}."
                continue

            if pending_escape_actor:
                if "успеш" in low:
                    add_priority(f"{pending_escape_actor} вырывается из боя.")
                elif "не удался" in low or "неуда" in low or "сорван" in low:
                    add_priority(f"{pending_escape_actor} пытается уйти, но побег срывается.")
                pending_escape_actor = None
                continue

        m_hp = hp_re.match(t)
        if m_hp and pending_attack:
            hp_name = clean_name(m_hp.group(1))
            if hp_name == pending_attack.target:
                try:
                    hp_cur = int(m_hp.group(2))
                    hp_max = int(m_hp.group(3))
                except Exception:
                    hp_cur, hp_max = -1, -1
                add_regular(pending_attack.outcome_fact or f"{pending_attack.attacker} атакует {pending_attack.target}.")
                state_fact = hp_state_fact(pending_attack.target, hp_cur, hp_max)
                if state_fact:
                    add_regular(state_fact)
                pending_attack = None
            continue

        if "повержен" in low:
            add_priority("Противник повержен.")
            continue
        if low.startswith("победа"):
            add_priority("Победа — бой окончен.")
            continue
        if low.startswith("поражение"):
            add_priority("Поражение — отряд выбывает.")
            continue
        if low.startswith("бой заверш"):
            add_priority("Бой завершён.")
            continue

    if pending_attack:
        add_regular(pending_attack.outcome_fact or f"{pending_attack.attacker} атакует {pending_attack.target}.")

    facts: list[str] = []
    for item in facts_priority:
        if item and item not in facts:
            facts.append(item)
    for item in facts_regular:
        if item and item not in facts:
            facts.append(item)

    return facts[:10]
