# Pholio 📸 — LLM Reference

## Purpose

This document is a dense reference for an LLM assistant helping a developer work on Pholio. It covers the project's architecture, API, data schemas, layout algorithms, conventions, and decision rationale — written to let the LLM answer questions like "how does the lock mechanism work?", "what's the session JSON schema?", or "how do I add a new layout algorithm?".

Language of the application UI: French. This document is in English.

---

## Project in one sentence

Pholio is a local Python web app (FastAPI + browser UI) that takes a folder of photos and produces a PDF photo album, with automatic layout computation, manual overrides, session persistence, and multi-format page support.

---

## Stack

- **Runtime**: Python 3.11+, Poetry
- **Backend**: FastAPI + Uvicorn (single process, single worker)
- **Images**: Pillow (open, resize, EXIF, thumbnail)
- **PDF**: fpdf2
- **Frontend**: Vanilla HTML/CSS/JS + Interact.js (drag and resize)
- **Persistence**: JSON files in `sessions/`
- **Tests**: pytest + pytest-asyncio + httpx
- **Lint**: ruff (check + format) + mypy

---

## Source layout

```
src/pholio/
  cli.py            argparse + uvicorn start + webbrowser.open()
  main.py           FastAPI app factory, route wiring, static files
  config.py         PAGE_FORMATS dict, defaults
  layout.py         PhotoMeta, PageConfig, PhotoPlacement, LayoutResult, run_layout()
  pdf_export.py     generate_pdf(layout_result, album_path, jpeg_quality) -> bytes
  state.py          load_session(album) -> dict, save_session(album, data)
  image_utils.py    scan_album(), get_exif_meta(), get_or_create_thumbnail()
static/
  index.html        Shell HTML
  app.js            All UI logic
  styles.css
tests/
  conftest.py       AsyncClient fixture, test album fixture
  unit/             test_layout.py, test_pdf_export.py, test_image_utils.py, test_state.py
  integration/      test_api.py
```

---

## Key data contracts

### `PageConfig`
```python
@dataclass
class PageConfig:
    page_w_mm: float
    page_h_mm: float
    margin_mm: float      # same on all sides
    spacing_mm: float     # gap between photos
```

### `PhotoMeta`
```python
@dataclass
class PhotoMeta:
    id: str               # filename (unique within album)
    w_px: int
    h_px: int
    aspect: float         # w / h
```

### `PhotoPlacement`
```python
@dataclass
class PhotoPlacement:
    photo_id: str
    page: int             # 0-indexed
    x_mm: float           # from page left edge (including margin)
    y_mm: float           # from page top edge (including margin)
    w_mm: float
    h_mm: float
    locked: bool
```

### `LayoutResult`
```python
@dataclass
class LayoutResult:
    placements: list[PhotoPlacement]
    page_count: int
```

### Session JSON (v1)
```json
{
  "version": 1,
  "album_path": "images/Voyage à Prague",
  "config": {
    "page_format": "a4-landscape",
    "layout_type": "mosaic",
    "sort_order": "filename",
    "columns": 3,
    "margin_mm": 10,
    "spacing_mm": 5,
    "target_row_height_mm": 60,
    "relock_behaviour": "keep"
  },
  "photos": [
    {
      "id": "IMG_0097.jpg",
      "manual_order": 0,
      "locked": false,
      "override": null
    },
    {
      "id": "IMG_0098.jpg",
      "manual_order": 1,
      "locked": true,
      "override": { "page": 1, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 80.0, "h_mm": 60.0 }
    }
  ]
}
```

---

## `run_layout()` contract

```python
def run_layout(
    page_cfg: PageConfig,
    photos: list[PhotoMeta],
    layout_type: str,            # "grid" | "mosaic" | "columns"
    locked_overrides: dict[str, PhotoOverride],
    relock_behaviour: str,       # "keep" | "first" | "unlock"
) -> LayoutResult
```

### `relock_behaviour` semantics

| Value | Behaviour |
|---|---|
| `"keep"` | Locked photos are placed at their declared `override` position. The algorithm places unlocked photos in remaining space on each page. |
| `"first"` | Locked photos are placed first in the ordering (in their original relative order), then unlocked photos follow. All are re-flowed by the algorithm as if no locks existed. |
| `"unlock"` | All `override` data is ignored. Full recompute from scratch as if no photo was ever locked. |

---

## API routes

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/api/albums` | — | `[{name, path, count}]` |
| `GET` | `/api/albums/{name}/photos` | — | `[{id, w_px, h_px, aspect, exif_date, thumb_url}]` |
| `POST` | `/api/layout/compute` | `{config, photos}` | `LayoutResult` JSON |
| `POST` | `/api/layout/manual-move` | `{album, photo_id, page, x_mm, y_mm, config, photos}` | `LayoutResult` JSON |
| `POST` | `/api/layout/manual-resize` | `{album, photo_id, w_mm, h_mm, config, photos}` | `LayoutResult` JSON |
| `POST` | `/api/layout/toggle-lock` | `{photo_id, locked, config, photos}` | `LayoutResult` JSON |
| `GET` | `/api/session/{album}` | — | Session JSON |
| `POST` | `/api/session/{album}` | Session JSON | `{ok: true}` |
| `POST` | `/api/export/pdf` | `{album_path, layout_result, jpeg_quality}` | PDF binary |
| `GET` | `/thumbnails/{album}/{filename}` | — | WEBP image |

---

## Page formats

```python
PAGE_FORMATS = {
    "a4-landscape":      (297.0, 210.0),
    "a4-portrait":       (210.0, 297.0),
    "a3-landscape":      (420.0, 297.0),
    "a3-portrait":       (297.0, 420.0),
    "square-30":         (300.0, 300.0),
    "square-20":         (200.0, 200.0),
    "letter-landscape":  (279.4, 215.9),
    "letter-portrait":   (215.9, 279.4),
}
```

For `"custom"`, the caller provides `custom_w_mm` and `custom_h_mm`.

---

## Layout algorithms

### `grid`
- Divide `(page_w - 2*margin - (cols-1)*spacing)` by `cols` → cell width
- Cell height = cell width / aspect (use mean aspect if all same, or crop to square)
- Fill cells left-to-right, top-to-bottom; new page when bottom margin reached
- Locked photos: placed at their override; the cell slot at that position is skipped

### `mosaic` (justified layout)
- Target row height `target_row_height_mm` (configurable)
- For each candidate row: accumulate photos until sum of (photo_aspect * target_h) ≥ usable_width
- Scale that row so total width = usable_width exactly
- If scaled row doesn't fit remaining page height: new page
- Locked photos: inserted as a "forced row" of one photo at their declared position

### `columns` (masonry)
- Maintain array of column height accumulators (length = `cols`)
- For each photo: pick column with minimum height, place photo there
- Photo height = (col_width / photo_aspect)
- New page when any column would exceed usable height
- Locked photos: placed at override position; update the column accumulator for that column

---

## Thumbnail generation

- Path: `thumbnails/{slugify(album_name)}/{photo_id}.webp`
- Max side: 400 px (both axes, keep aspect ratio)
- EXIF orientation applied before resize
- Format: WEBP, quality 85
- Cache check: `thumbnail.stat().st_mtime > source.stat().st_mtime`

---

## Image format detection

Pholio calls `PIL.Image.open()` and catches `UnidentifiedImageError`. Supported extensions scanned: `.jpg`, `.jpeg`, `.png`, `.webp`, `.tiff`, `.tif`, `.bmp`.

---

## Testing conventions

- `conftest.py` provides: `async_client` (httpx AsyncClient), `test_album_path` (temp dir with 3 small test JPEGs)
- All async tests use `@pytest.mark.anyio`
- Layout unit tests create `PhotoMeta` lists directly (no file I/O)
- PDF tests write to a `BytesIO` and check page count and file size

---

## Common pitfalls

- **Pillow EXIF orientation**: always call `ImageOps.exif_transpose()` before any resize or dimension read
- **fpdf2 coordinate system**: origin is top-left, y increases downward, units are mm
- **Session JSON**: always validate `version` field on load; if absent or mismatched, return defaults
- **Layout with 0 photos**: return `LayoutResult(placements=[], page_count=0)` — do not crash
- **Custom page format**: if `page_format == "custom"`, require `custom_w_mm` and `custom_h_mm` in the request body
