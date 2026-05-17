# GitHub Copilot Instructions — Pholio 📸

## Language rules

- **Code and comments**: English only
- **Communication with the user**: French only
- **UI labels and user-facing text**: French
- **Documentation**:
  - `README.md`: French + English
  - User documentation (`doc/user/`): French
  - Technical and developer documentation (`doc/dev/`, `doc/plan.md`): English
  - `CHANGELOG.md`, release notes, backlog: French
  - Inline code comments: English only

---

## Project context

Pholio (📸) is a local web application for composing photo albums as PDFs from folders of images. The user runs `poetry run pholio` (or `python run.py`) and interacts via a browser at `localhost:8000`.

**Stack**: FastAPI + Pillow + fpdf2 + vanilla JS (Interact.js) + Poetry  
**Target**: single-user, runs locally on Windows, macOS or Linux  
See `doc/plan.md` for the full architecture plan and `doc/roadmap.md` for the roadmap.

---

## Development workflow

### Git Flow

This project follows **git flow**:
- `main` — production-ready releases only
- `develop` — integration branch, always runnable
- `feature/*` — new features branched from `develop`
- `fix/*` — bug fixes branched from `develop`
- `hotfix/*` — urgent fixes branched from `main`
- `release/*` — release preparation branched from `develop`

Never commit directly to `main` or `develop`.

### Branch naming

```
feature/short-description
fix/short-description
hotfix/short-description
release/x.y.z
```

### Commit messages

Follow **Conventional Commits** (`type(scope): description` in English):
- `feat(layout): add mosaic justified layout algorithm`
- `fix(pdf): correct image placement for landscape A4`
- `chore(deps): upgrade fpdf2 to 2.8`
- `docs(user): update manual with lock/unlock instructions`
- `test(layout): add unit tests for grid algorithm`

---

## TDD

Always write tests **before** implementing functionality:
1. Write a failing test describing the expected behaviour
2. Implement the minimum code to make it pass
3. Refactor, keeping tests green

Test coverage targets:
- Layout engine (`pholio/layout.py`): **≥ 90%**
- PDF export (`pholio/pdf_export.py`): **≥ 80%**
- API routes: **≥ 80%**
- Image utilities: **≥ 70%**

Test files mirror the source structure:
- `src/pholio/layout.py` → `tests/unit/test_layout.py`
- `src/pholio/main.py` (routes) → `tests/integration/test_api.py`
- `src/pholio/pdf_export.py` → `tests/unit/test_pdf_export.py`

---

## Quality control (pre-push)

Run the following checks **before every push**:

```powershell
ruff check src/ tests/
ruff format --check src/ tests/   # fix with: ruff format src/ tests/
python -m mypy src/
pytest tests/ -q
```

All checks must be green before pushing or opening a PR. Never bypass with `--no-verify`.

---

## Commit, push and PR workflow

When asked to commit, push and/or open a PR:

1. **Run the full quality gate** — all checks must be green
2. **Verify zero errors in VS Code**
3. **Commit** using Conventional Commits format
4. **Push** the branch
5. **Create the PR on GitHub** targeting the appropriate base branch:
   - `feature/*` → `develop`
   - `fix/*` → `main`
   - `release/*` → `main`
   - Request a **Copilot review** on the PR
6. **Address all review comments**, re-run the quality gate, push updates

---

## Architecture notes

### Layout engine (`pholio/layout.py`)

Three algorithms, all share the same interface `run_layout(config, photos) -> LayoutResult`:
- **grid**: regular N-column grid, all photos same size
- **mosaic**: justified layout (Flickr-style) — rows fill full width, photos keep aspect ratio
- **columns**: masonry N-column layout — each photo goes in the shortest column

**Lock mechanism**: locked photos are placed first at their fixed coordinates; the algorithm then flows unlocked photos in the remaining space. When a photo is moved/resized manually via the UI, it becomes locked automatically. The user can explicitly unlock it.

**Re-layout behaviour on lock conflict**: when relaunching a layout computation that includes locked photos, ask the user via a modal dialog:
- "Conserver les photos verrouillées à leur place" (default)
- "Remettre les photos verrouillées en premier (avant les autres)"
- "Déverrouiller toutes les photos et recalculer"

### Multi-format support

Page format is user-configurable. Supported values (handled in `pholio/config.py`):

| Key | Dimensions (mm) | Orientation |
|---|---|---|
| `a4-landscape` | 297 × 210 | landscape |
| `a4-portrait` | 210 × 297 | portrait |
| `a3-landscape` | 420 × 297 | landscape |
| `a3-portrait` | 297 × 420 | portrait |
| `square-30` | 300 × 300 | — |
| `square-20` | 200 × 200 | — |
| `letter-landscape` | 279.4 × 215.9 | landscape |
| `letter-portrait` | 215.9 × 279.4 | portrait |
| `custom` | user-defined width × height | — |

### State persistence

Sessions are stored as JSON in `sessions/{album_slug}.json`. Schema: see `doc/plan.md`.

### Image format support

Primary: JPEG. Extended (if Pillow can open it): PNG, WEBP, TIFF, BMP. Not yet planned: RAW formats.

---

## Documentation maintenance

| Document | Language | Location | Trigger |
|---|---|---|---|
| `README.md` | FR + EN | root | Every release |
| User manual | FR | `doc/user/manuel.md` | Feature added or modified |
| Developer docs | EN | `doc/dev/` | Architecture or API changed |
| `CHANGELOG.md` | FR | root | Every PR merged into `develop` |
| `doc/backlog.md` | FR | `doc/` | Ticket created, progressed, or completed |
| `doc/roadmap.md` | EN | `doc/` | Lot completed or reprioritised |
| `doc/plan.md` | EN | `doc/` | Architecture decisions updated |

---

## Project planning workflow

1. **Create tickets** in `doc/backlog.md` (format: `PHO-NNN`, priorities P1–P3)
   - Estimation formula: raw time × 1.15, rounded to 5 min
   - Lot total: sum of tickets + 15 min user project management
2. **Group into lots** and assign a target version
3. **Update roadmap** for each new feature lot
4. **Implement** on a feature branch, PR into develop
5. **Update docs** (CHANGELOG, user manual if applicable, backlog)

### Timing

- Record start/end time per ticket in `/memories/session/timing.md`
- After each completed lot: report actuals in `doc/backlog.md` and Calibration table
- If estimate ratio differs from 1.15 by > 20%, adjust margin and inform the user
