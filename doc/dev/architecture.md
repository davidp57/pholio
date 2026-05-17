# Pholio 📸 — Architecture

## Overview

Pholio is a single-process local web application. When the user runs `poetry run pholio`, the following happens:

1. `pholio/cli.py` parses CLI arguments
2. Uvicorn starts a FastAPI server on the chosen port (default 8000)
3. The system browser opens at `http://localhost:8000`
4. The user interacts with the HTML/JS frontend, which calls the FastAPI API
5. All state is stored locally in `sessions/`

---

## Module responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Entry point: argparse, uvicorn launch, browser open |
| `main.py` | FastAPI app factory, route registration, static file serving |
| `config.py` | Page format registry, default settings |
| `image_utils.py` | Album scan, EXIF metadata, thumbnail generation, format detection |
| `layout.py` | Layout algorithms (grid, mosaic, columns), lock mechanism |
| `pdf_export.py` | PDF assembly using fpdf2 |
| `state.py` | Session JSON save/load |

---

## Request flow

```
Browser  →  GET /api/layout/compute  →  main.py router
                                         ↓
                                    layout.run_layout()
                                         ↓
                                    LayoutResult JSON  →  Browser renders canvas
```

```
Browser  →  POST /api/export/pdf  →  main.py router
                                      ↓
                                 pdf_export.generate_pdf()
                                      ↓
                                 PDF bytes  →  Browser downloads file
```

---

## Data flow: thumbnail serving

```
Browser requests /thumbnails/voyage-prague/IMG_0097.jpg.webp
  → image_utils.get_or_create_thumbnail()
    → if thumbnails/{album}/{file}.webp exists and is newer than source: serve it
    → else: Pillow open → apply EXIF rotation → resize to 400px max → save WEBP
  → FastAPI FileResponse
```

---

## Layout algorithm overview

All three algorithms implement the same contract:

```python
def run_layout(
    page_cfg: PageConfig,
    photos: list[PhotoMeta],
    layout_type: str,
    locked_overrides: dict[str, PhotoOverride],
    relock_behaviour: str,
) -> LayoutResult
```

The `relock_behaviour` parameter controls what happens to already-locked photos:
- `"keep"`: locked photos stay at their declared position; unlocked photos flow around them
- `"first"`: locked photos are moved to the front of the ordering but then reflowed like unlocked
- `"unlock"`: all locks are cleared, full recompute from scratch

---

## Testing strategy

| Test type | Location | What it covers |
|---|---|---|
| Unit | `tests/unit/test_layout.py` | Layout algorithms, edge cases, lock behaviour |
| Unit | `tests/unit/test_pdf_export.py` | PDF assembly (with small test images) |
| Unit | `tests/unit/test_image_utils.py` | EXIF reading, thumbnail generation |
| Unit | `tests/unit/test_state.py` | Session JSON round-trip |
| Integration | `tests/integration/test_api.py` | API routes with HTTPX test client |

pytest-asyncio is used for async FastAPI tests. `conftest.py` provides an `AsyncClient` fixture.

---

## Adding a new layout algorithm

1. Implement a function `def layout_myalgo(page_cfg, photos, locked_overrides) -> list[PhotoPlacement]`
2. Register it in `run_layout()` dispatch table
3. Add the key to `config.py` allowed values
4. Write unit tests in `tests/unit/test_layout.py`
5. Add the option to the UI dropdown in `static/app.js`
