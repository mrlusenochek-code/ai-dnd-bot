from app.rules import encounters


class _ForcedRng:
    def __init__(self, value: float, pick: int = 0):
        self._value = value
        self._pick = pick

    def random(self) -> float:
        return self._value

    def randrange(self, n: int) -> int:
        if n <= 0:
            return 0
        return max(0, min(self._pick, n - 1))


def test_pick_encounter_is_deterministic_for_same_cell(monkeypatch):
    monkeypatch.setattr(
        encounters,
        "load_enemies_by_env",
        lambda env: [
            {"key": "city_rat", "cr": "1/8"},
            {"key": "city_bandit", "cr": "1"},
        ],
    )
    got1 = encounters.pick_encounter(seed="abc", x=3, y=7, env="город", party_level=1)
    got2 = encounters.pick_encounter(seed="abc", x=3, y=7, env="город", party_level=1)
    assert got1 == got2


def test_pick_encounter_respects_env_pool(monkeypatch):
    def _stub_load(env: str):
        if env == "город":
            return [{"key": "city_guard", "cr": "1"}]
        return [{"key": "forest_wolf", "cr": "1"}]

    monkeypatch.setattr(encounters, "load_enemies_by_env", _stub_load)
    got = encounters.pick_encounter(
        seed="seed",
        x=1,
        y=2,
        env="город",
        party_level=2,
        rng=_ForcedRng(0.0, pick=0),
    )
    assert got is not None
    assert got.enemy_key == "city_guard"


def test_pick_encounter_returns_none_when_cr_window_empty(monkeypatch):
    monkeypatch.setattr(
        encounters,
        "load_enemies_by_env",
        lambda env: [
            {"key": "city_dragon", "cr": "10"},
            {"key": "city_horror", "cr": "8"},
        ],
    )
    got = encounters.pick_encounter(
        seed="seed",
        x=10,
        y=10,
        env="город",
        party_level=1,
        rng=_ForcedRng(0.0),
    )
    assert got is None
