from app.rules.world_map import (
    init_world_state,
    move,
    world_seed_from_text,
    pick_chunk_env,
)


def test_world_seed_deterministic():
    s1 = world_seed_from_text("session_abc")
    s2 = world_seed_from_text("session_abc")
    assert s1 == s2


def test_chunk_env_deterministic():
    seed = 123
    a = pick_chunk_env(seed, 0, 0)
    b = pick_chunk_env(seed, 0, 0)
    assert a == b


def test_init_pregenerates_chunks():
    ws = init_world_state(seed=1, chunk_size=10, pregen_radius_chunks=2)
    # (2*2+1)^2 = 25
    assert len(ws.chunks) == 25


def test_move_generates_new_chunks_on_demand():
    ws = init_world_state(seed=1, chunk_size=10, pregen_radius_chunks=0)
    assert len(ws.chunks) == 1  # только 0,0
    ws, patch = move(ws, "e", view_radius_chunks=1)
    assert "pos" in patch and "new_chunks" in patch
    assert len(ws.chunks) >= 1
