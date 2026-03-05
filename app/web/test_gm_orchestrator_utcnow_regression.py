from __future__ import annotations


def test_gm_orchestrator_has_utcnow() -> None:
    from app.web import gm_orchestrator as m

    assert hasattr(m, "utcnow")
    assert callable(m.utcnow)
