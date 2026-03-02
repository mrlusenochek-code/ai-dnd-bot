from __future__ import annotations

import asyncio
from typing import Any

from app.gm import combat_narration
from app.web import server


def test_generate_wrapper_equals_module(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        return {"text": "Ты проводишь атаку и давишь на врага.\nЧто делаете дальше?"}

    monkeypatch.setattr(combat_narration, "generate_from_prompt", fake_generate_from_prompt)

    kwargs = {
        "campaign_title": "Кампания Бой",
        "outcome_summary": ["Ты атаковал и враг отступил."],
        "player_action": "combat_attack",
        "current_turn": "Раунд 2: Рин",
        "participants_block": "- PC: Рин\n- ENEMY: Гоблин",
        "actor_name": "Рин",
        "actor_gender": "м",
        "actor_pronouns": "он/его/ему",
    }
    out_wrapper = asyncio.run(server._generate_combat_narration(**kwargs))
    out_module = asyncio.run(
        combat_narration.generate_combat_narration(
            **kwargs,
            timeout_seconds=server.GM_OLLAMA_TIMEOUT_SECONDS,
            num_predict=max(240, server.GM_FINAL_NUM_PREDICT // 3),
        )
    )

    assert out_wrapper == out_module
    assert len(calls) == 2


def test_generate_from_facts_low_coverage_triggers_reprompt() -> None:
    calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(calls) == 1:
            return {"text": "Ты бьешь противника и теснишь его.\nЧто делаете дальше?"}
        return {"text": "Ты бьешь противника, он отступает и выглядит раненым.\nЧто делаете дальше?"}

    out = asyncio.run(
        combat_narration.generate_combat_narration_from_facts(
            combat_lock_prompt=server._COMBAT_LOCK_PROMPT,
            facts=[
                "Герой попадает по врагу.",
                "Враг ранен и отступает.",
            ],
            required_fact_count=2,
            scene_facts_block="- Зона игрока: тесный двор рядом с тобой\n- Окружение: камни и пыль.",
            player_raw_action="Атакую врага",
            player_name="Рин",
            ended=False,
            timeout_seconds=server.GM_OLLAMA_TIMEOUT_SECONDS,
            num_predict=server.GM_FINAL_NUM_PREDICT,
            mentions_forbidden_gear_fn=lambda _text: False,
            llm_generate=fake_generate_from_prompt,
        )
    )

    assert len(calls) == 2
    assert "ранен" in out.lower()
    assert out.endswith("Что делаете дальше?")


def test_generate_mentions_action_false_repaired_fallback(monkeypatch) -> None:
    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        return {"text": "Пыль клубится в узком проходе, противники сходятся ближе."}

    monkeypatch.setattr(combat_narration, "generate_from_prompt", fake_generate_from_prompt)

    out = asyncio.run(
        combat_narration.generate_combat_narration(
            campaign_title="Кампания Бой",
            outcome_summary=["Ты атаковал и оттеснил врага."],
            player_action="combat_attack",
            current_turn="Раунд 1",
            participants_block="- PC: Рин\n- ENEMY: Гоблин",
            actor_name="Рин",
            actor_gender="м",
            actor_pronouns="он/его/ему",
            timeout_seconds=server.GM_OLLAMA_TIMEOUT_SECONDS,
            num_predict=max(240, server.GM_FINAL_NUM_PREDICT // 3),
        )
    )

    assert "Ты проводишь атаку в гуще боя" in out
    assert out.endswith("Что делаете дальше?")
