# Pholio — Technical Plan

## TL;DR

Pholio is a local web application (single-user) that generates photo album PDFs from folders of JPEG images. The user runs one command; a browser window opens at `localhost:8000`. The app handles automatic layout computation, manual overrides with locking, session persistence, and high-resolution PDF export.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Backend | FastAPI + Uvicorn |
| Image processing | Pillow |
| PDF generation | fpdf2 |
| Frontend | Vanilla HTML/CSS/JS + Interact.js (drag/resize) |
| Persistence | JSON files (`sessions/`) |
| Package manager | Poetry |
| Testing | pytest + pytest-asyncio + httpx |
| Linting | ruff + mypy |

---

## Project structure

```
photos/                          ← workspace root (contains the images/ folder)
├── src/
│   └── pholio/
│       ├── __init__.py
│       ├── cli.py               ← entry point (argparse + uvicorn + open browser)
│       ├── main.py              ← FastAPI app factory + static file serving
│       ├── config.py            ← page formats, default settings
│       ├── layout.py            ← layout algorithms (grid, mosaic, columns)
│       ├── pdf_export.py        ← PDF generation (fpdf2)
│       ├── state.py             ← session save/load (JSON)
│       └── image_utils.py       ← EXIF reading, thumbnail generation, format detection
├── static/
│   ├── index.html
│   ├── app.js                   ← UI logic (fetch API, Interact.js, canvas render)
│   └── styles.css
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_layout.py
│   │   ├── test_pdf_export.py
│   │   ├── test_state.py
│   │   └── test_image_utils.py
│   └── integration/
│       └── test_api.py
├── images/                      ← user photo albums (one folder = one album)
├── thumbnails/                  ← auto-generated cache (gitignored)
├── sessions/                    ← session JSON files (gitignored)
├── doc/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── run.py                       ← shortcut: python run.py
```

---

## Session JSON schema

```json
{
  "version": 1,
  "album_path": "images/Voyage à Prague",
  "config": {
    "page_format": "a4-landscape",
    "layout_type": "mosaic",
    "sort_order": "filename",
    "columns": 3,
    "margin_top_mm": 10,
    "margin_right_mm": 10,
    "margin_bottom_mm": 10,
    "margin_left_mm": 10,
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
      "override": {
        "page": 1,
        "x_mm": 10.0,
        "y_mm": 10.0,
        "w_mm": 80.0,
        "h_mm": 60.0
      }
    }
  ]
}
```

### `relock_behaviour` values (chosen by user via modal on re-layout)

| Value | Behaviour |
|---|---|
| `"keep"` | Locked photos stay at their fixed position (default) |
| `"first"` | Locked photos are placed first before unlocked ones |
| `"unlock"` | All locks are cleared; full auto-layout from scratch |

---

## Page formats (`pholio/config.py`)

| Key | Width × Height (mm) |
|---|---|
| `a4-landscape` | 297 × 210 |
| `a4-portrait` | 210 × 297 |
| `a3-landscape` | 420 × 297 |
| `a3-portrait` | 297 × 420 |
| `square-30` | 300 × 300 |
| `square-20` | 200 × 200 |
| `letter-landscape` | 279.4 × 215.9 |
| `letter-portrait` | 215.9 × 279.4 |
| `custom` | user-supplied |

---

## Layout engine (`pholio/layout.py`)

### Data structures

```python
@dataclass
class PageConfig:
    page_w_mm: float
    page_h_mm: float
    margin_top_mm: float
    margin_right_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    spacing_mm: float

@dataclass
class PhotoMeta:
    id: str              # filename
    w_px: int
    h_px: int
    aspect: float        # w_px / h_px

@dataclass
class PhotoPlacement:
    photo_id: str
    page: int            # 0-indexed
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float
    locked: bool

@dataclass
class LayoutResult:
    placements: list[PhotoPlacement]
    page_count: int
```

### Algorithm: `grid`

- Divide usable width by N columns
- All photos same size (square crop or letterboxed)
- Fill left-to-right, top-to-bottom
- Locked photos occupy their declared slot; algorithm skips that cell

### Algorithm: `mosaic` (justified layout)

Adapted from Flickr's justified layout algorithm:
1. Group photos into rows targeting `target_row_height_mm`
2. Scale each row so the total width equals the usable page width
3. When a row would overflow the page, start a new page
4. Locked photos are rendered at their declared position; surrounding rows adapt

### Algorithm: `columns` (masonry)

- Maintain N column height accumulators
- Place each photo in the shortest column
- Locked photos update their column's height accumulator

### `run_layout(page_cfg, photos, locked_overrides, relock_behaviour, size_overrides, cover_photo_id) -> LayoutResult`

1. Separate locked and unlocked photos
2. Apply `relock_behaviour` (`keep` / `first` / `unlock`)
3. Dispatch to the chosen algorithm
4. Return `LayoutResult`

---

## API routes (`pholio/main.py`)

### Albums

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/albums` | List subfolders of `images/` |
| `GET` | `/api/albums/{name}/photos` | Scan album, generate thumbnails, return metadata |

### Layout

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/layout/compute` | Full layout recompute |
| `POST` | `/api/layout/manual-move` | Move one photo, lock it, recompute rest |
| `POST` | `/api/layout/manual-resize` | Resize one photo, lock it, recompute rest |
| `POST` | `/api/layout/toggle-lock` | Lock or unlock a photo |

### Session

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/session/{album}` | Load saved session or return defaults |
| `POST` | `/api/session/{album}` | Save current session |

### Export

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/export/pdf` | Generate and return PDF as binary download |

### Static

| Path | Description |
|---|---|
| `GET /thumbnails/{filename}` | Serve cached thumbnail |
| `GET /` | Serve `static/index.html` |

---

## Thumbnail generation (`pholio/image_utils.py`)

- On first access, generate a 400 px max-side WEBP thumbnail
- Store in `thumbnails/{album_slug}/{filename}.webp`
- Cache: if file exists and is newer than source, skip regeneration
- EXIF orientation is applied before thumbnail generation

---

## PDF export (`pholio/pdf_export.py`)

- Uses fpdf2 `FPDF` class
- One `add_page()` per page in `LayoutResult`
- For each `PhotoPlacement`: open source image with Pillow, apply EXIF rotation, place with `image(x=..., y=..., w=..., h=...)`
- JPEG quality: configurable (default 90)
- Returns `bytes` (streamed as a file download)

---

## Image format support

Pillow is used for all image I/O. Supported formats:
- **Primary**: JPEG (`.jpg`, `.jpeg`)
- **Extended**: PNG, WEBP, TIFF, BMP (detected by Pillow `Image.open()`)
- **Not planned**: RAW camera formats (CR2, NEF, ARW, etc.)

---

## Implementation roadmap

See `doc/roadmap.md` for the versioned delivery plan.
