"""Page format registry and application defaults."""

from __future__ import annotations

# Page format key -> (width_mm, height_mm)
PAGE_FORMATS: dict[str, tuple[float, float]] = {
    "a4-landscape": (297.0, 210.0),
    "a4-portrait": (210.0, 297.0),
    "a3-landscape": (420.0, 297.0),
    "a3-portrait": (297.0, 420.0),
    "square-30": (300.0, 300.0),
    "square-20": (200.0, 200.0),
    "letter-landscape": (279.4, 215.9),
    "letter-portrait": (215.9, 279.4),
}

LAYOUT_TYPES = ("grid", "mosaic", "columns")
SORT_ORDERS = ("filename", "exif_date", "manual")
RELOCK_BEHAVIOURS = ("keep", "first", "unlock")

DEFAULTS = {
    "page_format": "a4-landscape",
    "layout_type": "mosaic",
    "sort_order": "filename",
    "columns": 3,
    "margin_top_mm": 10.0,
    "margin_right_mm": 10.0,
    "margin_bottom_mm": 10.0,
    "margin_left_mm": 10.0,
    "spacing_mm": 5.0,
    "target_row_height_mm": 60.0,
    "relock_behaviour": "keep",
    "watermark_text": "",
}

THUMBNAIL_MAX_SIDE = 400
THUMBNAIL_QUALITY = 85
JPEG_EXPORT_QUALITY = 90

IMAGES_DIR = "images"
THUMBNAILS_DIR = "thumbnails"
SESSIONS_DIR = "sessions"
SESSION_SCHEMA_VERSION = 1
