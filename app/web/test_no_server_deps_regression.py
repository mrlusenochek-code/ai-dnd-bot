from pathlib import Path


APP_WEB_DIR = Path(__file__).resolve().parent


def test_http_routes_has_no_server_deps_pattern() -> None:
    src = (APP_WEB_DIR / "http_routes.py").read_text(encoding="utf-8")
    assert "app.web.server" not in src


def test_combat_bridge_has_no_server_deps_pattern() -> None:
    src = (APP_WEB_DIR / "combat_bridge.py").read_text(encoding="utf-8")
    assert "import app.web.server as deps" not in src
    assert "deps." not in src


def test_server_deps_gateway_is_limited() -> None:
    files_with_gateway: list[str] = []
    for path in APP_WEB_DIR.rglob("*.py"):
        if path.name.startswith("test_"):
            continue
        src = path.read_text(encoding="utf-8")
        if "import app.web.server as deps" in src:
            files_with_gateway.append(str(path.relative_to(APP_WEB_DIR.parent)))

    allowed = {
        "web/gm_orchestrator.py",
        "web/state_builder.py",
        "web/ws_handlers.py",
    }
    assert set(files_with_gateway).issubset(allowed)
    assert len(files_with_gateway) <= len(allowed)
