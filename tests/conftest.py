"""Pytest fixtures for Pholio tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image


@pytest.fixture(scope="session")
def test_album_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary album directory with 3 small test JPEGs."""
    album_dir = tmp_path_factory.mktemp("test_album")
    for i, name in enumerate(["IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg"]):
        img = Image.new("RGB", (400 + i * 100, 300), color=(200 - i * 30, 100, 150))
        img.save(album_dir / name, format="JPEG", quality=85)
    return album_dir


@pytest.fixture(scope="session")
def test_thumbnails_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Temporary thumbnails directory."""
    return tmp_path_factory.mktemp("thumbnails")


@pytest.fixture
async def async_client() -> AsyncClient:
    """AsyncClient wired to the FastAPI app under test."""
    from pholio.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
