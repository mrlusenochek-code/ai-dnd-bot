from __future__ import annotations

from typing import Any, Optional
import re


def build_combat_narration_from_patch(patch: dict[str, Any] | None, *, player_name: str | None) -> str | None:
    if not isinstance(patch, dict):
        return None
    lines = patch.get("lines")
    if not isinstance(lines, list) or not lines:
        return None

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    player_norm = norm(player_name or "").lower()

    def is_player(attacker: str) -> bool:
        a = norm(attacker).lower()
        return bool(player_norm) and (a == player_norm)

    attack_re = re.compile(r"^Атака:\s*(.+?)\s*→\s*(.+)\s*$", re.IGNORECASE)
    result_hit = ("попадание", "крит")
    result_miss = ("промах",)

    pending: tuple[str, str] | None = None
    out: list[str] = []

    def add_sentence(attacker: str, defender: str, ok: bool | None) -> None:
        atk_is_player = is_player(attacker)
        enemy_name = defender if atk_is_player else attacker
        if ok is True:
            if atk_is_player:
                out.append(f"Ты находишь момент и попадаешь по противнику — {enemy_name} отшатывается.")
            else:
                out.append(f"{enemy_name} бросается на тебя и задевает ударом.")
        elif ok is False:
            if atk_is_player:
                out.append(f"Ты бросаешься в атаку, но {enemy_name} успевает уйти от удара.")
            else:
                out.append(f"{enemy_name} атакует, но ты уходишь в сторону в последний момент.")
        else:
            # неизвестный исход — очень нейтрально
            if atk_is_player:
                out.append("Ты атакешь, стараясь не дать противнику опомниться.")
            else:
                out.append(f"{enemy_name} пытается перехватить инициативу.")

    for it in lines:
        text = None
        kind = None
        if isinstance(it, dict):
            text = it.get("text")
            kind = it.get("kind")
        elif isinstance(it, str):
            text = it
        if not isinstance(text, str) or not text.strip():
            continue

        t = text.strip()

        # игнорим чисто техстроки/механику/разделители/статусы
        if t == "====================":
            continue
        if kind == "status" or t.startswith("⚔"):
            continue
        if t.startswith("Бросок") or t.startswith("Урон:") or " vs AC " in t or "HP " in t:
            continue
        if t.startswith("Ход автоматически передан"):
            continue
        if t.startswith("Противник добавлен") or t.startswith("Добавлен в бой:") or t.startswith("Бой начался между"):
            continue

        m = attack_re.match(t)
        if m:
            pending = (m.group(1).strip(), m.group(2).strip())
            continue

        if pending and t.lower().startswith("результат:"):
            low = t.lower()
            ok: Optional[bool] = None
            if any(w in low for w in result_hit):
                ok = True
            if any(w in low for w in result_miss):
                ok = False
            add_sentence(pending[0], pending[1], ok)
            pending = None
            continue

        if "повержен" in t.lower():
            out.append("Противник падает без сил.")
            continue
        if t.lower().startswith("победа"):
            out.append("Схватка окончена — опасность миновала.")
            continue
        if t.lower().startswith("бой заверш"):
            out.append("Бой завершён.")
            continue

    if pending:
        add_sentence(pending[0], pending[1], None)

    # не раздуваем: максимум 3 предложения
    out = [s for s in out if s]
    if not out:
        return None
    out = out[:3]
    return " ".join(out)
