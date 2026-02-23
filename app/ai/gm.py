import asyncio
import json
import os
from typing import Any, Sequence, Optional
from urllib import request


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_LORE_MODEL = os.getenv("OLLAMA_LORE_MODEL", OLLAMA_MODEL)
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("GM_OLLAMA_TIMEOUT_SECONDS", "30"))


def build_gm_prompt(session_title: str, context_events: Sequence[str]) -> str:
    lines = [line.strip() for line in context_events if isinstance(line, str) and line.strip()]
    context = "\n".join(f"- {line}" for line in lines[-50:]) or "- (контекст пуст)"
    title = (session_title or "Кампания").strip()
    return (
        "Ты мастер настольной RPG. Отвечай только по-русски.\n"
        "Контекст сцены (последние события):\n"
        f"{context}\n\n"
        "Дай короткий ответ мастера (1-3 предложения), который двигает сцену вперёд.\n"
        "Если уместно, добавь отдельной строкой: Проверка: <stat_or_skill> DC <N>.\n"
        "Не пиши мета-комментарии, не упоминай, что ты модель/ИИ.\n"
        f"Название сессии: {title}"
    )


def _post_generate_json(*, model: str, prompt: str, timeout_seconds: float, num_predict: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": int(num_predict)},
    }
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=float(timeout_seconds)) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _ollama_to_response_dict(data: dict[str, Any]) -> dict[str, Any]:
    text = str(data.get("response") or "").strip()
    finish_reason = str(data.get("done_reason") or data.get("finish_reason") or "").strip().lower()
    usage = {
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_count": data.get("eval_count"),
        "total_duration": data.get("total_duration"),
        "load_duration": data.get("load_duration"),
        "prompt_eval_duration": data.get("prompt_eval_duration"),
        "eval_duration": data.get("eval_duration"),
    }
    # server.py ожидает именно ключ "text"
    return {"text": text, "finish_reason": finish_reason, "usage": usage}


async def generate_from_prompt(
    *,
    prompt: str,
    timeout_seconds: Optional[float] = None,
    num_predict: Optional[int] = None,
) -> dict[str, Any]:
    """
    Совместимо с app/web/server.py:
      await generate_from_prompt(prompt=..., timeout_seconds=..., num_predict=...)
    Возвращает dict с ключами: text, finish_reason, usage
    """
    timeout = float(timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS)
    predict = int(num_predict if num_predict is not None else 512)
    try:
        data = await asyncio.to_thread(
            _post_generate_json,
            model=OLLAMA_MODEL,
            prompt=str(prompt or ""),
            timeout_seconds=timeout,
            num_predict=predict,
        )
        return _ollama_to_response_dict(data)
    except Exception as e:
        # не падаем — пусть server.py включит свои fallback-и
        return {"text": "", "finish_reason": "error", "usage": {}, "error": str(e)}


def build_lore_prompt(session_title: str, setting_text: str) -> str:
    title = (session_title or "Кампания").strip()
    setting = (setting_text or "").strip()
    return (
        "Ты Мастер настольной RPG в стиле D&D. Отвечай только по-русски.\n"
        "Сгенерируй вступительный ЛОР кампании и стартовую сцену.\n"
        "Запрещены мета-комментарии и заголовки 'Анализ/Ответ'. Пиши как мастер.\n"
        "Тон: приключение, атмосферно, без жести.\n\n"
        "Жёсткие правила:\n"
        "1) Не используй для NPC реальные этничности/национальности/\"расы\" (например 'кавказец' и подобные); описывай по роли/внешности и давай имя или прозвище.\n"
        "2) Держи фэнтезийный тон: без современных стереотипов и сленга; строго следуй вайбу текста сеттинга пользователя.\n"
        "3) Не зацикливай NPC на бесконечном разговоре: дай ясный хук сцены, но оставь игрокам возможность спокойно disengage/уйти.\n\n"
        f"Название кампании: {title}\n"
        f"Сеттинг от пользователя:\n{setting}\n\n"
        "Выдай:\n"
        "1) Короткий лор мира (6-12 предложений).\n"
        "2) Стартовую сцену (6-12 предложений), где герои оказываются в ситуации, требующей решения.\n"
        "3) В конце строку: 'Что делаете дальше?'\n"
        "4) Затем 2-4 нейтральных варианта действий списком (без оценок и морали).\n"
    )


async def generate_lore(
    *,
    # Поддерживаем оба варианта вызова:
    # 1) server.py: generate_lore(session_title=..., setting_text=..., timeout_seconds=...)
    session_title: Optional[str] = None,
    setting_text: Optional[str] = None,
    # 2) запасной: generate_lore(prompt="...")
    prompt: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
    num_predict: Optional[int] = None,
) -> dict[str, Any]:
    """
    Совместимо с app/web/server.py.
    Возвращает dict с ключами: text, finish_reason, usage
    """
    timeout = float(timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS)
    predict = int(num_predict if num_predict is not None else 900)

    if prompt is None:
        prompt = build_lore_prompt(
            session_title=str(session_title or ""),
            setting_text=str(setting_text or ""),
        )

    try:
        data = await asyncio.to_thread(
            _post_generate_json,
            model=OLLAMA_LORE_MODEL,
            prompt=str(prompt or ""),
            timeout_seconds=timeout,
            num_predict=predict,
        )
        return _ollama_to_response_dict(data)
    except Exception as e:
        return {"text": "", "finish_reason": "error", "usage": {}, "error": str(e)}
