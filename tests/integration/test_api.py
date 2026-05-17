"""Integration tests for the FastAPI API."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from pholio.config import SESSION_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_list_albums_empty(
    async_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    response = await async_client.get("/api/albums")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_albums_with_folders(
    async_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "images" / "Album A").mkdir(parents=True)
    (tmp_path / "images" / "Album B").mkdir(parents=True)
    response = await async_client.get("/api/albums")
    assert response.status_code == 200
    names = [a["name"] for a in response.json()]
    assert "Album A" in names
    assert "Album B" in names


@pytest.mark.asyncio
async def test_session_roundtrip(
    async_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    data = {
        "version": SESSION_SCHEMA_VERSION,
        "album_path": "images/test",
        "config": {"page_format": "a4-landscape"},
        "photos": [],
    }
    save_response = await async_client.post("/api/session/test", json=data)
    assert save_response.status_code == 200
    assert save_response.json() == {"ok": True}

    load_response = await async_client.get("/api/session/test")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["album_path"] == "images/test"


@pytest.mark.asyncio
async def test_session_defaults_when_missing(
    async_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    response = await async_client.get("/api/session/does-not-exist")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 1
    assert "config" in data
