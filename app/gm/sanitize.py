import re
from typing import Optional

COMBAT_NARRATION_BANNED_RE = re.compile(
    r"\b(?:урон|ac|hp|d20|проверка|бросок|dc)\b",
    flags=re.IGNORECASE,
)

GM_META_BANNED_PHRASES = (
    "сцена продолжается",
    "если вы хотите",
    "я могу помочь",
    "могу предложить",
    "могу дать информацию",
    "если у вас есть вопросы",
    "чтобы продолжить историю",
    "дальнейшее развитие сюжета",
)


def _strip_machine_lines(text: str) -> str:
    out: list[str] = []
    for line in (text or "").splitlines():
        if line.strip().startswith("@@CHECK"):
            continue
        if line.strip().startswith("@@CHECK_RESULT"):
            continue
        # ВАЖНО: @@ZONE_SET НЕ вырезаем здесь, иначе команда пропадёт до парсинга в _extract_machine_commands.
        out.append(line)
    return "\n".join(out).strip()


def _enforce_ty_singular_fixes(text: str) -> str:
    txt = str(text or "")

    placeholders: list[str] = []

    def _mask_quoted(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"__QUOTE_PLACEHOLDER_{len(placeholders) - 1}__"

    txt = re.sub(r"«[^»]*»|\"(?:[^\"\\]|\\.)*\"", _mask_quoted, txt)

    def _case_first(src: str, replacement: str) -> str:
        if not src:
            return replacement
        if src[0].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    def _replace_case_aware(pattern: str, replacement: str) -> None:
        nonlocal txt

        def _repl(m: re.Match[str]) -> str:
            return _case_first(m.group(0), replacement)

        txt = re.sub(pattern, _repl, txt, flags=re.IGNORECASE)

    phrase_replacements = [
        (r"\bс\s+вами\b", "с тобой"),
        (r"\bу\s+вас\b", "у тебя"),
        (r"\bк\s+вам\b", "к тебе"),
    ]
    for pattern, replacement in phrase_replacements:
        _replace_case_aware(pattern, replacement)

    verb_replacements = [
        (r"\bвы\s+видите\b", "ты видишь"),
        (r"\bвы\s+замечаете\b", "ты замечаешь"),
        (r"\bвы\s+слышите\b", "ты слышишь"),
        (r"\bвы\s+чувствуете\b", "ты чувствуешь"),
        (r"\bвы\s+понимаете\b", "ты понимаешь"),
        (r"\bвы\s+можете\b", "ты можешь"),
        (r"\bвы\s+начинаете\b", "ты начинаешь"),
        (r"\bвы\s+пытаетесь\b", "ты пытаешься"),
        (r"\bвы\s+смотрите\b", "ты смотришь"),
        (r"\bвы\s+решаете\b", "ты решаешь"),
    ]
    for pattern, replacement in verb_replacements:
        _replace_case_aware(pattern, replacement)

    def _fix_ty_verb(m: re.Match[str]) -> str:
        pronoun = m.group(1)
        verb = m.group(2)
        verb_l = verb.lower()
        if verb_l.endswith("ёте"):
            fixed = verb[:-3] + "ёшь"
        elif verb_l.endswith("ете"):
            fixed = verb[:-3] + "ешь"
        elif verb_l.endswith("ите"):
            fixed = verb[:-3] + "ишь"
        else:
            return m.group(0)
        fixed = _case_first(verb, fixed)
        return f"{_case_first(pronoun, 'ты')} {fixed}"

    txt = re.sub(r"\b(вы)\s+([А-Яа-яЁё]+)(?=[\s,.;:!?)]|$)", _fix_ty_verb, txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bВы\s+(?=\w+(?:ешь|ишь)\b)", "Ты ", txt)

    word_replacements = [
        (r"\bвами\b", "тобой"),
        (r"\bваша\b", "твоя"),
        (r"\bваше\b", "твоё"),
        (r"\bваши\b", "твои"),
        (r"\bваш\b", "твой"),
        (r"\bвас\b", "тебя"),
        (r"\bвам\b", "тебе"),
        (r"\bвы\b", "ты"),
    ]
    for pattern, replacement in word_replacements:
        _replace_case_aware(pattern, replacement)

    def _fix_nanoshite(m: re.Match[str]) -> str:
        token = m.group(0)
        return "Наносишь" if token[:1].isupper() else "наносишь"

    txt = re.sub(r"наношите", _fix_nanoshite, txt, flags=re.IGNORECASE)
    txt = re.sub(r"замечаете", lambda m: _case_first(m.group(0), "замечаешь"), txt, flags=re.IGNORECASE)

    def _unmask_quotes(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return placeholders[idx]

    txt = re.sub(r"__QUOTE_PLACEHOLDER_(\d+)__", _unmask_quotes, txt)
    return txt


def sanitize_gm_output(text: str) -> str:
    max_len_without_question = 1800
    long_repeat_line_min_len = 80
    txt = str(text or "").strip()
    if not txt:
        return ""
    txt = re.sub(r"<think\b[^>]*>.*?</think\s*>", " ", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"</?think\b[^>]*>", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"@@CHECK_RESULT", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"@@CHECK", "", txt, flags=re.IGNORECASE)

    lines = txt.splitlines()
    first_nonempty_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if str(line).strip():
            first_nonempty_idx = i
            break
    if first_nonempty_idx is not None:
        first_line = lines[first_nonempty_idx]
        if re.match(r"^\s*(анализ|analysis)\b", first_line, flags=re.IGNORECASE):
            lines.pop(first_nonempty_idx)
            first_nonempty_idx = None
            for i, line in enumerate(lines):
                if str(line).strip():
                    first_nonempty_idx = i
                    break
    if first_nonempty_idx is not None:
        first_line = lines[first_nonempty_idx]
        m_response = re.match(r"^\s*(ответ|final answer|response|финальный ответ)\b\s*:?\s*(.*)$", first_line, flags=re.IGNORECASE)
        if m_response:
            tail = str(m_response.group(2) or "").strip()
            if tail:
                lines[first_nonempty_idx] = tail
            else:
                lines.pop(first_nonempty_idx)
    txt = "\n".join(lines)
    txt = re.sub(r"(?<=[А-Яа-яЁё])[A-Za-z]+|[A-Za-z]+(?=[А-Яа-яЁё])", "", txt)
    leaked_word_map = {
        "moment": "момент",
        "continues": "продолжает",
        "business": "дело",
        "financial": "финансовый",
    }
    for en_word, ru_word in leaked_word_map.items():
        txt = re.sub(rf"\b{re.escape(en_word)}\b", ru_word, txt, flags=re.IGNORECASE)
    txt = re.sub(r"(?<![A-Za-z])[A-Za-z]{3,}(?![A-Za-z])", "", txt)

    cleaned_lines: list[str] = []
    for line in txt.splitlines():
        ln = line.strip()
        if re.match(r"^(финальный|итоговый)\s+ответ\b[:\s-]*$", ln, flags=re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    txt = "\n".join(cleaned_lines)

    mechanic_line_patterns = [
        re.compile(
            r"^\s*[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'()\- ]{1,60}:\s*\d{1,3}\s*\([+-]?\d{1,3}\)\s*=\s*\d{1,3}"
            r"(?:\s*\((?:успех|успешно|провал|success|fail(?:ed)?)\))?\s*$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^\s*[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'()\- ]{1,60}\s+\d{1,3}\s*\([+-]?\d{1,3}\)\s*=\s*\d{1,3}"
            r"(?:\s*\((?:успех|успешно|провал|success|fail(?:ed)?)\))?\s*$",
            flags=re.IGNORECASE,
        ),
        re.compile(r"^\s*(?:\d*d20|d20)\s*:?\s*\d{1,3}(?:\s*[+-]\s*\d{1,3})+\s*=\s*\d{1,3}\s*$", flags=re.IGNORECASE),
        re.compile(r"^\s*\d+\s*d\s*\d+(?:\s*[+-]\s*\d+)*\s*=\s*\d+\s*$", flags=re.IGNORECASE),
        re.compile(
            r"^\s*(?:dc|кс)\s*[:=]?\s*\d{1,3}(?:\s*(?:успех|успешно|провал|success|fail(?:ed)?))?\s*$",
            flags=re.IGNORECASE,
        ),
    ]
    mechanic_inline_patterns = [
        r"\b(?:\d*d20|d20)\s*:?\s*\d{1,3}(?:\s*[+-]\s*\d{1,3})+\s*=\s*\d{1,3}\b",
        r"\b\d+\s*d\s*\d+(?:\s*[+-]\s*\d+)*\s*=\s*\d+\b",
        r"\b[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'()\- ]{1,60}:\s*\d{1,3}\s*\([+-]?\d{1,3}\)\s*=\s*\d{1,3}(?:\s*\((?:успех|успешно|провал|success|fail(?:ed)?)\))?",
        r"\b[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'()\- ]{1,60}\s+\d{1,3}\s*\([+-]?\d{1,3}\)\s*=\s*\d{1,3}(?:\s*\((?:успех|успешно|провал|success|fail(?:ed)?)\))?",
        r"\b(?:dc|кс)\s*[:=]?\s*\d{1,3}(?:\s*(?:успех|успешно|провал|success|fail(?:ed)?))?\b",
    ]
    filtered_lines: list[str] = []
    for line in txt.splitlines():
        if any(p.match(line.strip()) for p in mechanic_line_patterns):
            continue
        filtered_lines.append(line)
    txt = "\n".join(filtered_lines)
    for pattern in mechanic_inline_patterns:
        txt = re.sub(pattern, "", txt, flags=re.IGNORECASE)

    txt = re.sub(
        r"\b(?:fails?|succeeds?|успех|провал)\b\s+на\s+проверке\b[^()\n]{0,240}"
        r"(?:\(\s*результат\s*:[^)\n]{0,120}\))?",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(
        r"\b(?:успех|провал|fails?|succeeds?)\b\s+на\s+проверке\b[^()\n]{0,240}",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(
        r"\(\s*(?:результат|result)\s*:\s*(?:успех|провал|fails?|succeeds?)\s*\)",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(
        r"\b(?:результат|result)\s*:\s*(?:успех|провал|fails?|succeeds?)\b",
        "",
        txt,
        flags=re.IGNORECASE,
    )

    txt = re.sub(
        r"(извиняюсь|извини(?:те)?|прошу прощения)[^.!?\n]{0,160}(я\s+)?не\s+могу[^.!?\n]{0,220}[.!?]?",
        "Сцена продолжается.",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(r"\bя\s+не\s+могу[^.!?\n]{0,260}[.!?]?", "Сцена продолжается.", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bне\s+могу\s+продолжить[^.!?\n]{0,260}[.!?]?", "Сцена продолжается.", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bAppears to be\b[^.!?\n]{0,120}[.!?]?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(
        r"\bвы\s+(?:решили|решаете|выбрали|выбираете|делаете\s+выбор)\b[^.!?\n]{0,220}[.!?]?",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(r"\bправильно\s+ли\s+ты\s+(?:должна|должен)\b", "стоит ли тебе", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bты\s+(?:должна|должен|должны)\b", "тебе нужно", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\bты\s+(?:могла|мог)\s+бы\b", "ты можешь", txt, flags=re.IGNORECASE)
    txt = txt.replace(". ты можешь", ". Ты можешь")
    txt = txt.replace("\nты можешь", "\nТы можешь")
    txt = re.sub(
        r"(?im)^\s*[\"'«»“”„]?\s*мастер\s+обрабатывает(?:\s+действие)?\b[^\n]*\n?",
        "",
        txt,
    )
    txt = re.sub(
        r"(?im)\s*[\"'«»“”„]?\s*мастер\s+обрабатывает(?:\s+действие)?\b[^\n]*",
        "",
        txt,
    )
    txt = re.sub(
        r"(?im)^\s*начн[её]м\s+с\s+последнего\s+действия\s+игрока\.\s*$\n?",
        "",
        txt,
    )
    txt = re.sub(
        r"(?im)^\s*(?:теперь\s+очередь\s+следующего\s+действия\s+игрока|теперь\s+очередь\s+следующего\s+хода\s+игрока|теперь\s+очередь\s+следующего\s+действия)\.?\s*$\n?",
        "",
        txt,
    )
    txt = re.sub(
        r"(?is)^\s*(?:теперь\s+очередь\s+следующего\s+действия\s+игрока|теперь\s+очередь\s+следующего\s+хода\s+игрока|теперь\s+очередь\s+следующего\s+действия)\.?\s*",
        "",
        txt,
    )

    fragments = re.findall(r"[^.!?\n]+[.!?]*|\n+", txt, flags=re.DOTALL)
    kept: list[str] = []
    for frag in fragments:
        if not frag:
            continue
        if frag.isspace() and "\n" in frag:
            kept.append(frag)
            continue
        normalized = re.sub(r"\s+", " ", frag).strip().lower()
        if normalized and any(phrase in normalized for phrase in GM_META_BANNED_PHRASES):
            continue
        kept.append(frag)
    txt = "".join(kept)

    deduped_lines: list[str] = []
    variants_header_seen = False
    prev_norm = ""
    long_line_repeat_counts: dict[str, int] = {}
    for line in txt.splitlines():
        stripped = line.strip()
        if re.match(r"^варианты\s+действий\s*:?\s*$", stripped, flags=re.IGNORECASE):
            if variants_header_seen:
                continue
            variants_header_seen = True
            line = "Варианты действий:"
            stripped = line
        if stripped and not stripped.startswith("@@"):
            if (
                re.search(r"[A-Za-z]", stripped)
                and not re.search(r"[А-Яа-яЁё]", stripped)
                and len(re.findall(r"[A-Za-z]{2,}", stripped)) >= 2
            ):
                continue
        norm = re.sub(r"\s+", " ", stripped).strip().lower()
        if norm and norm == prev_norm:
            continue
        if norm and len(norm) >= long_repeat_line_min_len:
            seen = long_line_repeat_counts.get(norm, 0)
            if seen >= 2:
                continue
            long_line_repeat_counts[norm] = seen + 1
        if norm:
            prev_norm = norm
        deduped_lines.append(line)
    txt = "\n".join(deduped_lines)

    lines = txt.splitlines()
    header_re = re.compile(r"^\s*варианты\s+действий\s*:?\s*$", flags=re.IGNORECASE)
    list_item_re = re.compile(r"^\s*(?:[-*•]\s+.+|\d+[.)]\s+.+)$")
    without_options: list[str] = []
    i = 0
    while i < len(lines):
        if header_re.match(lines[i].strip()):
            i += 1
            removed = 0
            while i < len(lines) and removed < 10:
                ln = lines[i]
                if list_item_re.match(ln.strip()):
                    i += 1
                    removed += 1
                    continue
                if not ln.strip():
                    i += 1
                    continue
                break
            continue
        without_options.append(lines[i])
        i += 1
    txt = "\n".join(without_options)

    lines = txt.splitlines()
    q_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if re.search(r"что\s+делаете\s+дальше\??", line, flags=re.IGNORECASE):
            q_idx = i
            break
    if q_idx is not None:
        lines[q_idx] = "Что делаете дальше?"
        txt = "\n".join(lines[: q_idx + 1])
    elif len(txt) > max_len_without_question:
        clipped = txt[:max_len_without_question]
        cut_pos = max(clipped.rfind("\n"), clipped.rfind(". "), clipped.rfind("! "), clipped.rfind("? "))
        if cut_pos > max_len_without_question // 2:
            clipped = clipped[:cut_pos]
        clipped = clipped.strip()
        txt = (clipped + "\nЧто делаете дальше?").strip()

    txt = re.sub(r"[ \t]{2,}", " ", txt)
    txt = re.sub(r"[ \t]*\n[ \t]*", "\n", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    txt = txt.strip(" \n\r\t-")

    cyr_count = len(re.findall(r"[А-Яа-яЁё]", txt))
    lat_count = len(re.findall(r"[A-Za-z]", txt))
    if (cyr_count < 20 and lat_count > 40) or (lat_count > cyr_count * 2 and lat_count > 30):
        return "Сцена продолжается.\nЧто делаете дальше?"
    prompt_only = re.sub(r"\s+", " ", txt).strip()
    if prompt_only in ("", "Что делаете дальше?"):
        return "Сцена продолжается.\nЧто делаете дальше?"
    return _enforce_ty_singular_fixes(txt)


def sanitize_combat_narration(text: str) -> str:
    txt = sanitize_gm_output(_strip_machine_lines(str(text or "").strip()))
    txt = re.sub(r"(?im)^\s*@@[A-Z_]+.*$", "", txt).strip()
    txt = re.sub(r"(?im)^\s*(?:\*|-)\s+.*$", "", txt)
    txt = re.sub(r"(?im)^\s*\d+\)\s+.*$", "", txt)
    txt = re.sub(r"(?im)^\s*\d+\.\s+.*$", "", txt)
    txt = re.sub(r"[«\"“][^\"»”\n]{0,240}[»\"”]", "", txt)
    txt = COMBAT_NARRATION_BANNED_RE.sub("", txt)
    txt = re.sub(r"\d+", "", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    txt = re.sub(r"[ \t]*\n[ \t]*", "\n", txt)
    txt = txt.strip(" \n\r\t-")
    txt = _enforce_ty_singular_fixes(txt)
    if not txt:
        txt = (
            "Схватка не стихает, сталь и крики сливаются в единый гул.\n"
            "Противники давят, но ты удерживаешь темп и ищешь окно для манёвра.\n"
            "Инициатива всё ещё в твоих руках."
        )
    if not re.search(r"что\s+делаете\s+дальше\??\s*$", txt, flags=re.IGNORECASE):
        txt = txt.rstrip(".!? \n") + "\nЧто делаете дальше?"
    txt = re.sub(r"(?im)^что\s+делаете\s+дальше\??\s*$", "Что делаете дальше?", txt)
    return txt.strip()
