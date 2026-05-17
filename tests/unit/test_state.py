"""Unit tests for session state persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pholio.config import DEFAULTS, SESSION_SCHEMA_VERSION


class TestSessionRoundtrip:
    def test_save_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from pholio.state import load_session, save_session

        data = {
            "version": SESSION_SCHEMA_VERSION,
            "album_path": "images/test",
            "config": dict(DEFAULTS),
            "photos": [
                {"id": "IMG_0001.jpg", "manual_order": 0, "locked": False, "override": None}
            ],
        }
        save_session("test", data)
        loaded = load_session("test")
        assert loaded["album_path"] == "images/test"
        assert loaded["photos"][0]["id"] == "IMG_0001.jpg"

    def test_load_missing_returns_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        from pholio.state import load_session

        result = load_session("nonexistent_album")
        assert result["version"] == SESSION_SCHEMA_VERSION
        assert result["config"] == DEFAULTS
        assert result["photos"] == []

    def test_load_corrupt_json_returns_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "corrupt.json").write_text("not valid json", encoding="utf-8")

        from pholio.state import load_session

        result = load_session("corrupt")
        assert result["version"] == SESSION_SCHEMA_VERSION

    def test_load_wrong_version_returns_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        data = {"version": 99, "album_path": "old", "config": {}, "photos": []}
        (sessions_dir / "old-album.json").write_text(json.dumps(data), encoding="utf-8")

        from pholio.state import load_session

        result = load_session("old album")
        assert result["version"] == SESSION_SCHEMA_VERSION
