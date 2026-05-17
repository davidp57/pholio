"""Build a standalone Windows/macOS/Linux executable using PyInstaller.

Usage:
    poetry run pholio-build            # one-dir bundle (default)
    poetry run pholio-build --onefile  # single-file exe (slower first launch)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Pholio standalone executable.")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a single-file exe instead of a one-dir bundle.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Not used directly; kept for forward compatibility.",
    )
    args = parser.parse_args()

    # Check that PyInstaller is available in the current environment
    try:
        import importlib.util

        if importlib.util.find_spec("PyInstaller") is None:
            raise ModuleNotFoundError
    except ModuleNotFoundError:
        print(
            "PyInstaller is not installed.\n"
            "Run:  poetry run pip install pyinstaller\n"
            "Then: poetry run pholio-build",
            file=sys.stderr,
        )
        sys.exit(1)

    # Paths
    here = Path(__file__).parent  # src/pholio/
    src_dir = here.parent  # src/
    root = src_dir.parent  # project root
    static_dir = root / "static"
    entry = here / "cli.py"

    sep = os.pathsep  # ";" on Windows, ":" on Unix

    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "pholio",
        "--noconfirm",
        "--noupx",
        # Bundle the entire pholio package (not statically traceable from cli.py)
        "--collect-submodules",
        "pholio",
        # Bundle the static web UI
        "--add-data",
        f"{static_dir}{sep}static",
        # Collect data files from libraries that rely on package-internal assets
        "--collect-data",
        "PIL",
        # Uvicorn hidden imports (not auto-detected by PyInstaller)
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols",
        "--hidden-import",
        "uvicorn.protocols.http",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.http.h11_impl",
        "--hidden-import",
        "uvicorn.protocols.websockets",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        "--hidden-import",
        "uvicorn.lifespan",
        "--hidden-import",
        "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "--hidden-import",
        "fastapi",
        "--hidden-import",
        "fastapi.staticfiles",
        "--hidden-import",
        "starlette.routing",
        "--hidden-import",
        "starlette.staticfiles",
        # Entry point
        str(entry),
    ]

    if args.onefile:
        cmd.append("--onefile")
    # else: default --onedir (faster startup, no temp-dir extraction)

    print("Running PyInstaller…")
    subprocess.run(cmd, check=True, cwd=str(root))
    print()
    if args.onefile:
        print("Done. Executable: dist/pholio.exe  (or dist/pholio on Unix)")
    else:
        print("Done. Bundle: dist/pholio/")
        print("  Run with: dist/pholio/pholio.exe  (or dist/pholio/pholio on Unix)")
        print("  Place your 'images/' folder next to the exe before launching.")
