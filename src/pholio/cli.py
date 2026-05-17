"""CLI entry point: parse arguments, start uvicorn, open browser."""

from __future__ import annotations

import argparse
import multiprocessing
import webbrowser


def main() -> None:
    # Required for PyInstaller frozen executables on Windows (multiprocessing spawn)
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        prog="pholio",
        description="Pholio — Photo album PDF generator",
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

    import uvicorn

    url = f"http://{args.host}:{args.port}"
    print(f"\n  \U0001f4f8 Pholio  \u2192  {url}")
    print("  Ctrl+C pour quitter\n", flush=True)
    webbrowser.open(url)

    uvicorn.run(
        "pholio.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
