"""Image utilities: album scan, EXIF metadata, thumbnail generation."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from pholio.config import THUMBNAIL_MAX_SIDE, THUMBNAIL_QUALITY, THUMBNAILS_DIR

try:
    from pillow_heif import register_heif_opener as _register_heif

    _register_heif()
    _HEIF_AVAILABLE = True
except ImportError:
    _HEIF_AVAILABLE = False

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"}
if _HEIF_AVAILABLE:
    SUPPORTED_EXTENSIONS |= {".heic", ".heif"}


def slugify(text: str) -> str:
    """Convert a string to a safe folder name."""
    slug = text.lower()
    # Remove non-ASCII and non-word chars (keeping spaces and dashes), ASCII only
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.ASCII)
    # Replace each whitespace char individually with a hyphen
    slug = re.sub(r"\s", "-", slug)
    return slug.strip("-")


def scan_album(album_path: Path) -> list[dict[str, object]]:
    """Scan an album folder and return sorted metadata for each supported image.

    Args:
        album_path: Path to the album directory.

    Returns:
        List of dicts with keys: id, path, w_px, h_px, exif_date.
        Sorted by filename by default.
    """
    results = []
    for f in sorted(album_path.iterdir()):
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            with Image.open(f) as img:
                oriented: Image.Image = ImageOps.exif_transpose(img) or img
                w, h = oriented.size
            exif_date = _read_exif_date(f)
            results.append(
                {
                    "id": f.name,
                    "path": str(f),
                    "w_px": w,
                    "h_px": h,
                    "exif_date": exif_date,
                }
            )
        except (UnidentifiedImageError, Exception):
            # Skip unreadable files silently
            continue
    return results


def _read_exif_date(path: Path) -> str | None:
    """Read DateTimeOriginal from EXIF data. Returns ISO string or None."""
    try:
        with Image.open(path) as img:
            exif = img._getexif()  # type: ignore[attr-defined]
            if exif:
                # Tag 36867 = DateTimeOriginal
                raw = exif.get(36867)
                if raw:
                    return str(raw)
    except Exception:
        pass
    return None


def get_or_create_thumbnail(source_path: Path, album_name: str) -> Path:
    """Return the path to a cached thumbnail, generating it if needed.

    Args:
        source_path: Full path to the source image.
        album_name: Album folder name (used to namespace thumbnails).

    Returns:
        Path to the WEBP thumbnail file.
    """
    thumb_dir = Path(THUMBNAILS_DIR) / slugify(album_name)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / (source_path.name + ".webp")

    # Use cached thumbnail if it exists and is up to date
    if thumb_path.exists() and thumb_path.stat().st_mtime >= source_path.stat().st_mtime:
        return thumb_path

    with Image.open(source_path) as raw:
        oriented = ImageOps.exif_transpose(raw)
        oriented.thumbnail((THUMBNAIL_MAX_SIDE, THUMBNAIL_MAX_SIDE), Image.Resampling.LANCZOS)
        oriented.save(thumb_path, format="WEBP", quality=THUMBNAIL_QUALITY)

    return thumb_path
