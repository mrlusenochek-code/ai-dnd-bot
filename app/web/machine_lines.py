import ast
import re
from typing import Any, Optional

from app.rules.equipment_slots import EquipmentSlot
from app.web.regexes import INV_MACHINE_LINE_RE, ZONE_SET_MACHINE_LINE_RE


def _as_int(s: Any, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


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


def _split_machine_args(args_raw: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    in_quote: Optional[str] = None
    depth = 0
    esc = False
    for ch in str(args_raw or ""):
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if in_quote:
            cur.append(ch)
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            cur.append(ch)
            in_quote = ch
            continue
        if ch in ("[", "{", "("):
            depth += 1
            cur.append(ch)
            continue
        if ch in ("]", "}", ")"):
            depth = max(0, depth - 1)
            cur.append(ch)
            continue
        if ch == "," and depth == 0:
            token = "".join(cur).strip()
            if token:
                parts.append(token)
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_machine_value(raw: str) -> Any:
    src = str(raw or "").strip()
    if not src:
        return ""
    if re.fullmatch(r"[+-]?\d+", src):
        return _as_int(src, 0)
    if src[0] in ("'", '"', "[", "{", "("):
        try:
            return ast.literal_eval(src)
        except Exception:
            pass
    return src


def _parse_inventory_machine_line(line: str) -> Optional[dict[str, Any]]:
    m = INV_MACHINE_LINE_RE.match(str(line or ""))
    if not m:
        return None
    cmd = str(m.group("cmd") or "").strip().upper()
    args_raw = str(m.group("args") or "")
    fields: dict[str, Any] = {}
    for token in _split_machine_args(args_raw):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        k = str(key or "").strip().lower()
        if not k:
            continue
        fields[k] = _parse_machine_value(value)

    if cmd == "INV_ADD":
        uid = _as_int(fields.get("uid"), 0)
        name = str(fields.get("name") or "").strip()
        if uid <= 0 or not name:
            return None
        tags: Optional[list[str]] = None
        tags_raw = fields.get("tags")
        if isinstance(tags_raw, (list, tuple)):
            tag_vals: list[str] = []
            for tag in tags_raw:
                t = str(tag or "").strip()
                if not t:
                    continue
                tag_vals.append(t[:30])
                if len(tag_vals) >= 8:
                    break
            if tag_vals:
                tags = tag_vals
        notes = str(fields.get("notes") or "").strip()[:200]
        return {
            "op": "add",
            "uid": uid,
            "name": name[:80],
            "qty": _clamp(_as_int(fields.get("qty"), 1), 1, 99),
            "tags": tags,
            "notes": notes or None,
        }
    if cmd == "INV_REMOVE":
        uid = _as_int(fields.get("uid"), 0)
        name = str(fields.get("name") or "").strip()
        if uid <= 0 or not name:
            return None
        return {
            "op": "remove",
            "uid": uid,
            "name": name[:80],
            "qty": _clamp(_as_int(fields.get("qty"), 1), 1, 99),
        }
    if cmd == "INV_TRANSFER":
        from_uid = _as_int(fields.get("from_uid"), 0)
        to_uid = _as_int(fields.get("to_uid"), 0)
        name = str(fields.get("name") or "").strip()
        if from_uid <= 0 or to_uid <= 0 or not name:
            return None
        return {
            "op": "transfer",
            "from_uid": from_uid,
            "to_uid": to_uid,
            "name": name[:80],
            "qty": _clamp(_as_int(fields.get("qty"), 1), 1, 99),
        }
    if cmd == "EQUIP":
        uid = _as_int(fields.get("uid"), 0)
        name = str(fields.get("name") or "").strip()
        slot_raw = str(fields.get("slot") or "").strip().lower()
        if uid <= 0 or not name or not slot_raw:
            return None
        try:
            slot = EquipmentSlot(slot_raw)
        except Exception:
            return None
        return {"op": "equip", "uid": uid, "name": name[:80], "slot": slot.value}
    if cmd == "UNEQUIP":
        uid = _as_int(fields.get("uid"), 0)
        slot_raw = str(fields.get("slot") or "").strip().lower()
        if uid <= 0 or not slot_raw:
            return None
        try:
            slot = EquipmentSlot(slot_raw)
        except Exception:
            return None
        return {"op": "unequip", "uid": uid, "slot": slot.value}
    return None


def _parse_zone_set_machine_line(line: str) -> Optional[dict[str, Any]]:
    m = ZONE_SET_MACHINE_LINE_RE.match(str(line or ""))
    if not m:
        return None
    args_raw = str(m.group("args") or "")
    fields: dict[str, Any] = {}
    for token in _split_machine_args(args_raw):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        k = str(key or "").strip().lower()
        if not k:
            continue
        fields[k] = _parse_machine_value(value)

    uid = _as_int(fields.get("uid"), 0)
    zone = str(fields.get("zone") or "").strip()
    if uid <= 0 or not zone:
        return None
    return {"uid": uid, "zone": zone[:80]}
