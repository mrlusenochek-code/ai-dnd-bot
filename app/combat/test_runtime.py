from dataclasses import dataclass


@dataclass
class CombatTestEnemyState:
    enemy_id: str
    name: str
    hp_current: int
    hp_max: int
    ac: int


@dataclass
class CombatTestRuntime:
    session_id: str
    active: bool
    round_no: int
    turn_order_labels: list[str]
    turn_index: int
    enemy: CombatTestEnemyState
    player_name: str
    player_hp_current: int
    player_hp_max: int
    player_ac: int
    attack_seq: int = 0
    enemy_attack_seq: int = 0


_TEST_COMBAT_BY_SESSION: dict[str, CombatTestRuntime] = {}


def start_test_combat(session_id: str) -> CombatTestRuntime:
    runtime = CombatTestRuntime(
        session_id=session_id,
        active=True,
        round_no=1,
        turn_order_labels=["Персонаж #1", "Разбойник"],
        turn_index=0,
        enemy=CombatTestEnemyState(
            enemy_id="bandit_1",
            name="Разбойник",
            hp_current=18,
            hp_max=18,
            ac=13,
        ),
        player_name="Персонаж #1",
        player_hp_current=20,
        player_hp_max=20,
        player_ac=14,
    )
    _TEST_COMBAT_BY_SESSION[session_id] = runtime
    return runtime


def get_test_combat(session_id: str) -> CombatTestRuntime | None:
    return _TEST_COMBAT_BY_SESSION.get(session_id)


def clear_test_combat(session_id: str) -> None:
    _TEST_COMBAT_BY_SESSION.pop(session_id, None)


def advance_turn(session_id: str) -> CombatTestRuntime | None:
    runtime = get_test_combat(session_id)
    if runtime is None or not runtime.active or not runtime.turn_order_labels:
        return None
    prev_turn_index = runtime.turn_index
    runtime.turn_index = (runtime.turn_index + 1) % len(runtime.turn_order_labels)
    if runtime.turn_index == 0 and prev_turn_index != 0:
        runtime.round_no += 1
    return runtime


def apply_enemy_damage(session_id: str, damage: int) -> CombatTestRuntime | None:
    runtime = get_test_combat(session_id)
    if runtime is None or not runtime.active:
        return None
    runtime.enemy.hp_current = max(0, runtime.enemy.hp_current - max(0, int(damage)))
    return runtime


def apply_player_damage(session_id: str, damage: int) -> CombatTestRuntime | None:
    runtime = get_test_combat(session_id)
    if runtime is None or not runtime.active:
        return None
    runtime.player_hp_current = max(0, runtime.player_hp_current - max(0, int(damage)))
    return runtime


def current_turn_label(runtime: CombatTestRuntime) -> str:
    if not runtime.turn_order_labels:
        return "-"
    if runtime.turn_index < 0 or runtime.turn_index >= len(runtime.turn_order_labels):
        return "-"
    return runtime.turn_order_labels[runtime.turn_index]
