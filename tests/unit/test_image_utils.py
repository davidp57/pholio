"""Unit tests for image utilities."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


class TestSlugify:
    def test_basic(self) -> None:
        from pholio.image_utils import slugify

        assert slugify("Voyage à Prague") == "voyage--prague"

    def test_spaces_to_hyphens(self) -> None:
        from pholio.image_utils import slugify

        assert slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self) -> None:
        from pholio.image_utils import slugify

        result = slugify("Album (2024)!")
        assert "(" not in result
        assert "!" not in result


class TestScanAlbum:
    def test_returns_jpg_files(self, test_album_dir: Path) -> None:
        from pholio.image_utils import scan_album

        results = scan_album(test_album_dir)
        assert len(results) == 3
        assert all(r["id"].endswith(".jpg") for r in results)

    def test_returns_dimensions(self, test_album_dir: Path) -> None:
        from pholio.image_utils import scan_album

        results = scan_album(test_album_dir)
        for r in results:
            assert r["w_px"] > 0
            assert r["h_px"] > 0

    def test_ignores_non_image_files(self, tmp_path: Path) -> None:
        from pholio.image_utils import scan_album

        (tmp_path / "readme.txt").write_text("not an image", encoding="utf-8")
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(tmp_path / "photo.jpg", format="JPEG")
        results = scan_album(tmp_path)
        assert len(results) == 1
        assert results[0]["id"] == "photo.jpg"

    def test_sorted_by_filename(self, test_album_dir: Path) -> None:
        from pholio.image_utils import scan_album

        results = scan_album(test_album_dir)
        ids = [r["id"] for r in results]
        assert ids == sorted(ids)


class TestSupportedExtensions:
    def test_heic_in_supported_extensions_when_pillow_heif_available(self) -> None:
        """HEIC extension is supported when pillow-heif is installed."""
        from pholio.image_utils import _HEIF_AVAILABLE, SUPPORTED_EXTENSIONS

        if _HEIF_AVAILABLE:
            assert ".heic" in SUPPORTED_EXTENSIONS
            assert ".heif" in SUPPORTED_EXTENSIONS
        else:
            # pillow-heif not installed: extensions not added to avoid false positives
            assert ".heic" not in SUPPORTED_EXTENSIONS

    def test_base_formats_always_supported(self) -> None:
        from pholio.image_utils import SUPPORTED_EXTENSIONS

        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            assert ext in SUPPORTED_EXTENSIONS


class TestThumbnail:
    def test_creates_thumbnail(
        self, test_album_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        from pholio.image_utils import get_or_create_thumbnail

        source = test_album_dir / "IMG_0001.jpg"
        thumb = get_or_create_thumbnail(source, "test_album")
        assert thumb.exists()
        assert thumb.suffix == ".webp"

    def test_thumbnail_max_size(
        self, test_album_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        from pholio.image_utils import get_or_create_thumbnail

        source = test_album_dir / "IMG_0001.jpg"
        thumb = get_or_create_thumbnail(source, "test_album")
        with Image.open(thumb) as img:
            assert max(img.size) <= 400

    def test_cached_thumbnail_not_regenerated(
        self, test_album_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        from pholio.image_utils import get_or_create_thumbnail

        source = test_album_dir / "IMG_0001.jpg"
        thumb1 = get_or_create_thumbnail(source, "test_album")
        mtime1 = thumb1.stat().st_mtime
        thumb2 = get_or_create_thumbnail(source, "test_album")
        assert thumb1 == thumb2
        assert thumb2.stat().st_mtime == mtime1
