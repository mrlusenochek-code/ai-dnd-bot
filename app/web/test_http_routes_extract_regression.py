from pathlib import Path


def test_server_has_no_http_route_decorators_and_keeps_ws() -> None:
    server_src = Path(__file__).with_name("server.py").read_text(encoding="utf-8")
    assert "@app.get(" not in server_src
    assert "@app.post(" not in server_src
    assert "@app.put(" not in server_src
    assert "@app.patch(" not in server_src
    assert "@app.delete(" not in server_src
    assert '@app.websocket("/ws/{session_id}")' not in server_src
    assert "http_router" not in server_src
    assert "include_router" not in server_src
    assert "server_impl" in server_src


def test_http_routes_module_defines_router_and_routes() -> None:
    routes_src = Path(__file__).with_name("http_routes.py").read_text(encoding="utf-8")
    assert "router = APIRouter()" in routes_src
    assert (
        "@router.get(" in routes_src
        or "@router.post(" in routes_src
        or "@router.put(" in routes_src
        or "@router.patch(" in routes_src
        or "@router.delete(" in routes_src
    )
