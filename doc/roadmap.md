# Pholio 📸 — Roadmap

## Version overview

| Version | Nom | Statut | Description |
|---|---|---|---|
| v0.1 | Setup | 🔲 En cours | Project scaffold, poetry, gitflow, TDD infra |
| v0.2 | Core | 🔲 Planifié | Image scan, thumbnails, session persistence, API skeleton |
| v0.3 | Layout | 🔲 Planifié | 3 layout algorithms (grid, mosaic, columns), lock mechanism |
| v0.4 | UI | 🔲 Planifié | Interactive browser UI — drag, resize, lock toggle, re-layout |
| v0.5 | PDF | 🔲 Planifié | PDF export, multi-format page support |
| v1.0 | Release | 🔲 Planifié | Stable release, full documentation |

---

## v0.1 — Setup

**Goal**: Working development environment. The project runs, tests pass, quality gate is green.

- Poetry project with all dependencies
- Git flow structure (main / develop branches)
- ruff + mypy + pytest configured
- Source skeleton (`src/pholio/`, `tests/`)
- Initial documentation (plan, roadmap, backlog)

---

## v0.2 — Core

**Goal**: The app starts, discovers albums, generates thumbnails, and can save/load a session.

- `pholio/cli.py`: parse CLI args, start uvicorn, open browser
- `pholio/image_utils.py`: scan album folder, read EXIF, generate thumbnails
- `pholio/state.py`: save/load session JSON
- `pholio/config.py`: page format registry
- API routes: `/api/albums`, `/api/albums/{name}/photos`, `/api/session/*`, `/thumbnails/*`

---

## v0.3 — Layout Engine

**Goal**: Given a list of photos and a config, compute placements for all 3 algorithms.

- `pholio/layout.py`: `grid`, `mosaic`, `columns` algorithms
- Lock mechanism: `run_layout()` with `relock_behaviour` (keep / first / unlock)
- API routes: `/api/layout/compute`, `/api/layout/manual-move`, `/api/layout/manual-resize`, `/api/layout/toggle-lock`
- Unit tests ≥ 90% coverage on `layout.py`

---

## v0.4 — Interactive UI

**Goal**: Full browser UI — album selection, config panel, interactive canvas with drag/resize/lock.

- `static/index.html`: structure (sidebar + canvas + toolbar)
- `static/app.js`: album picker, config form, layout rendering, Interact.js integration
- `static/styles.css`: layout, responsiveness
- Lock icon per photo, unlock click handler
- Sort panel (filename / date / drag-to-reorder)
- Re-layout modal (keep / first / unlock locked photos)

---

## v0.5 — PDF Export

**Goal**: Export the current layout as a high-resolution PDF.

- `pholio/pdf_export.py`: fpdf2 PDF assembly from `LayoutResult`
- Multi-format page support (A4, A3, square, letter, custom)
- EXIF orientation correction
- API route: `POST /api/export/pdf`
- Integration test covering export of a small album

---

## v1.0 — Stable Release

**Goal**: Production-ready, documented, tested.

- All quality gates green
- User manual (`doc/user/manuel.md`) complete
- LLM reference (`doc/llm/reference.md`) complete
- CHANGELOG frozen for v1.0
- `README.md` updated with final quick-start

---

## Not yet planned

- Dark mode
- Custom watermark / logo on pages
- Page title / caption text overlaid on photos
- Batch export (all albums at once)
- RAW image format support (CR2, NEF, ARW)
- Photo slideshow / reordering by drag in a filmstrip panel
