"""CLI entry point: parse arguments, start uvicorn, open browser."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pholio",
        description="Pholio — Photo album PDF generator",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Path to the album folder to open on startup",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    # Validate folder if provided
    if args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists():
            parser.error(f"Folder not found: {args.folder}")

    import uvicorn

    url = f"http://{args.host}:{args.port}"
    webbrowser.open(url)

    uvicorn.run(
        "pholio.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=False,
    )
