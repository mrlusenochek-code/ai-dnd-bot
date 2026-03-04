"""
Wiring-only FastAPI entrypoint.

Implementation lives in app.web.server_impl.
This module must stay thin to prevent domain logic from creeping back.
"""

from __future__ import annotations

import sys as _sys

from app.web import server_impl as _impl

# Keep module-level monkeypatch/import semantics identical to historical
# app.web.server by making this module an alias of app.web.server_impl.
_sys.modules[__name__] = _impl
