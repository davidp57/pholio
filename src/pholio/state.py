"""Session persistence: save and load album sessions as JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pholio.config import DEFAULTS, SESSION_SCHEMA_VERSION, SESSIONS_DIR
from pholio.image_utils import slugify


def _session_path(album_name: str) -> Path:
    sessions_dir = Path(SESSIONS_DIR)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir / f"{slugify(album_name)}.json"


def load_session(album_name: str) -> dict[str, Any]:
    """Load a saved session for an album, or return defaults if none exists.

    Args:
        album_name: The album folder name.

    Returns:
        Session dict with keys: version, album_path, config, photos.
    """
    path = _session_path(album_name)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version") == SESSION_SCHEMA_VERSION:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "version": SESSION_SCHEMA_VERSION,
        "album_path": f"images/{album_name}",
        "config": dict(DEFAULTS),
        "photos": [],
    }


def save_session(album_name: str, data: dict[str, Any]) -> None:
    """Save a session dict to disk.

    Args:
        album_name: The album folder name (used for file naming).
        data: The session dict to persist.
    """
    path = _session_path(album_name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
