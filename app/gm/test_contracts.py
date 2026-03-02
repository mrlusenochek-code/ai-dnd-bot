import hashlib

from app.gm import contracts
from app.web import server


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sample_turn_args() -> dict:
    return {
        "session_title": " Тестовая сессия ",
        "context_events": ["Игрок: осматриваюсь", "GM: эхо в коридоре"],
        "actor_uid": 7,
        "actors_block": "- uid=7, player=P1, character=Рин",
        "positions_block": "- Рин (#7): древний зал",
    }


def _sample_round_args() -> dict:
    return {
        "session_title": " Кампания X ",
        "lore_text": "Лор и легенды",
        "recent_events": ["Событие A", "Событие B"],
        "player_actions": ["Рин идёт вперёд", "Тор зажигает факел"],
        "master_notes": "держать темп",
        "difficulty": "hard",
        "actors_block": "- uid=7, player=P1, character=Рин\n- uid=8, player=P2, character=Тор",
        "positions_block": "- Рин (#7): зал\n- Тор (#8): коридор",
    }


def _sample_finalize_args() -> dict:
    return {
        "draft_text": "Черновой текст",
        "check_results": [
            {
                "actor_uid": 7,
                "kind": "skill",
                "name": "perception",
                "dc": 14,
                "roll": 12,
                "mod": 3,
                "total": 15,
                "success": True,
                "mode": "normal",
                "reason": "осмотр",
            }
        ],
    }


def _sample_combat_narration_args() -> dict:
    return {
        "campaign_title": " Кампания Бой ",
        "outcome_summary": ["Ты наносишь удар и оттесняешь врага."],
        "current_turn": "Раунд 2: Рин",
        "participants_block": "- PC: Рин\n- ENEMY: Гоблин",
        "actor_name": "Рин",
        "actor_gender": "м",
        "actor_pronouns": "он/его/ему",
    }


def test_combat_lock_prompt_wrapper_and_snapshot() -> None:
    out_contracts = contracts.COMBAT_LOCK_PROMPT
    out_server = server._COMBAT_LOCK_PROMPT
    assert out_server == out_contracts
    assert _sha256(out_contracts) == "390b7f59482e9d1fb527586182b7dceef6b5c56b3c45dd1493287dc01b0873a3"


def test_turn_draft_prompt_wrapper_and_snapshot() -> None:
    kwargs = _sample_turn_args()
    out_contracts = contracts.build_turn_draft_prompt(**kwargs)
    out_server = server._build_turn_draft_prompt(**kwargs)
    assert out_server == out_contracts
    assert _sha256(out_contracts) == "bc312d5aea6ae98a17cec6528d67cd66196a07ea4f02200b35f7f335f8ae6d39"


def test_round_draft_prompt_wrapper_and_snapshot() -> None:
    kwargs = _sample_round_args()
    out_contracts = contracts.build_round_draft_prompt(**kwargs)
    out_server = server._build_round_draft_prompt(**kwargs)
    assert out_server == out_contracts
    assert _sha256(out_contracts) == "9872f6cd381a861908e496af038b1f6ca4ed16d3ab07f929fc11a6d784984dfe"


def test_finalize_prompt_wrapper_and_snapshot() -> None:
    kwargs = _sample_finalize_args()
    out_contracts = contracts.build_finalize_prompt(**kwargs)
    out_server = server._build_finalize_prompt(**kwargs)
    assert out_server == out_contracts
    assert _sha256(out_contracts) == "ea29d8cb24e46655bcf118bcfae99daa164d3f6fb37e43575f9bf419753d1766"


def test_combat_narration_prompt_wrapper_and_snapshot() -> None:
    kwargs = _sample_combat_narration_args()
    out_contracts = contracts.build_combat_narration_prompt(**kwargs)
    out_server = server._build_combat_narration_prompt(**kwargs)
    assert out_server == out_contracts
    assert _sha256(out_contracts) == "ec656787a65063fa08ac68412f3ec5c944d9f5abf91824b0a5cd03a61470bb30"
