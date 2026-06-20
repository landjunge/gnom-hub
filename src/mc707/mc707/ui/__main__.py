"""``python -m mc707.ui`` — start the mc707 WebUI server.

Usage::

    python -m mc707.ui                                  # mock mode, port 8765
    python -m mc707.ui --port-name "MC-707 MIDI OUT"    # real hardware
    python -m mc707.ui --host 127.0.0.1 --port 9000     # custom bind
    python -m mc707.ui --sound-dir /path/to/sounds      # custom disk dir
    python -m mc707.ui --no-mock                        # require hardware
"""

from __future__ import annotations

import argparse
import logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m mc707.ui",
        description="Run the mc707 WebUI server (FastAPI + uvicorn).",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Bind port (default: 8765)",
    )
    parser.add_argument(
        "--port-name",
        default=None,
        help="MIDI output port name (omit for mock mode)",
    )
    parser.add_argument(
        "--device-id",
        type=lambda x: int(x, 0),
        default=0x00,
        help="Roland device ID 0x00..0x0F (default: 0x00)",
    )
    parser.add_argument(
        "--sound-dir",
        default=None,
        help="Directory for persisted sounds (default: ~/.mc707/sounds)",
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Disable mock mode — fail if no MIDI port is available",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable autoreload (development only)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging verbosity (default: info)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=args.log_level.upper())

    # Lazy import — uvicorn is only required when running the server,
    # not when importing mc707.ui elsewhere.
    import uvicorn

    from .app import create_app

    app = create_app(
        port_name=args.port_name,
        device_id=args.device_id,
        mock=not args.no_mock,
        sound_dir=args.sound_dir,
    )

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()