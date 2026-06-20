"""FastAPI application factory for the mc707 WebUI.

Use :func:`create_app` to build a configured FastAPI instance. The
factory wires up:

* CORS (open by default — fine for local dev; tighten for production)
* All routers from :mod:`mc707.ui.routes`
* The WebSocket endpoint from :mod:`mc707.ui.ws`
* A ``/health`` probe and ``/api/info`` JSON landing
* The bundled WebUI (under ``ui/static/``) served from ``/`` and
  ``/static/*`` — fully standalone, no external CDN required

Standalone run::

    uvicorn mc707.ui.app:app --host 0.0.0.0 --port 8765

Or via ``python -m mc707.ui`` which uses :mod:`mc707.ui.__main__`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .routes import ALL_ROUTERS
from .state import init_state
from .ws import router as ws_router

logger = logging.getLogger(__name__)

# Directory holding the bundled frontend (index.html + /css + /js).
# Sits next to this app.py — no external assets required at runtime.
STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def create_app(
    port_name: Optional[str] = None,
    device_id: int = 0x00,
    mock: bool = True,
    sound_dir: Optional[str] = None,
    cors_origins: Optional[list] = None,
) -> FastAPI:
    """Build a configured FastAPI app.

    Parameters
    ----------
    port_name:
        MIDI output port to open. ``None`` (or ``mock=True``) keeps the
        controller in mock mode.
    device_id:
        Roland device ID (0x00..0x0F) used in SysEx frames.
    mock:
        Force mock mode (default ``True``).
    sound_dir:
        Directory for :class:`SoundStore`. Defaults to ``~/.mc707/sounds``.
    cors_origins:
        Origins allowed by CORS. Defaults to ``["*"]`` which is fine for
        local dev. Tighten to specific origins in production.
    """
    init_state(
        port_name=port_name,
        device_id=device_id,
        mock=mock,
        sound_dir=sound_dir,
    )

    app = FastAPI(
        title="mc707 WebUI",
        version=__version__,
        description=(
            "Standalone HTTP + WebSocket interface to the Roland MC-707 "
            "MIDI controller. Works without hardware (mock mode)."
        ),
    )

    # CORS — open by default for local dev
    origins = cors_origins if cors_origins is not None else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    for router in ALL_ROUTERS:
        app.include_router(router)
    app.include_router(ws_router)

    # Health probe + landing
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/info", tags=["meta"])
    def info() -> dict:
        """JSON info — useful for non-browser clients."""
        return {
            "service": "mc707-webui",
            "version": __version__,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "websocket": "/ws",
            "ui": "/" if INDEX_HTML.exists() else None,
        }

    # ---- Frontend (static files) -------------------------------------
    # The bundled SPA lives under ``ui/static/``. We mount it on /static
    # so /static/css/style.css, /static/js/*.js etc. resolve. The root /
    # serves index.html directly so the browser lands on the UI by default.
    if STATIC_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="mc707-static",
        )

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            """Serve the bundled WebUI."""
            return FileResponse(str(INDEX_HTML), media_type="text/html")
    else:
        # No static dir → fall back to the original JSON landing.
        @app.get("/", tags=["meta"])
        def root() -> dict:
            return {
                "service": "mc707-webui",
                "version": __version__,
                "docs": "/docs",
                "openapi": "/openapi.json",
                "health": "/health",
                "websocket": "/ws",
            }

    logger.info("mc707 WebUI app created (mock=%s, ui=%s)", mock, INDEX_HTML.exists())
    return app


# Module-level app instance for ``uvicorn mc707.ui.app:app``.
# Default config: mock mode, default sound_dir.
app = create_app()


__all__ = ["create_app", "app"]