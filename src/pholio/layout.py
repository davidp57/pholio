"""Layout engine: grid, mosaic, and columns algorithms with lock support."""

from __future__ import annotations

from dataclasses import dataclass, field

# Height (mm) reserved at the top of the cover page for the album title
COVER_TITLE_H_MM: float = 20.0


@dataclass
class PageConfig:
    page_w_mm: float
    page_h_mm: float
    margin_top_mm: float
    margin_right_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    spacing_mm: float
    columns: int = 3
    target_row_height_mm: float = 60.0
    layout_type: str = "mosaic"

    @property
    def usable_w(self) -> float:
        return self.page_w_mm - self.margin_left_mm - self.margin_right_mm

    @property
    def usable_h(self) -> float:
        return self.page_h_mm - self.margin_top_mm - self.margin_bottom_mm


@dataclass
class PhotoMeta:
    id: str
    w_px: int
    h_px: int

    @property
    def aspect(self) -> float:
        return self.w_px / self.h_px if self.h_px > 0 else 1.0


@dataclass
class PhotoOverride:
    page: int
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


@dataclass
class SizeOverride:
    """Size-only constraint: layout places the photo freely but at this size."""

    w_mm: float
    h_mm: float


@dataclass
class PhotoPlacement:
    photo_id: str
    page: int
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float
    locked: bool = False


@dataclass
class LayoutResult:
    placements: list[PhotoPlacement] = field(default_factory=list)
    page_count: int = 0


def run_layout(
    page_cfg: PageConfig,
    photos: list[PhotoMeta],
    locked_overrides: dict[str, PhotoOverride],
    relock_behaviour: str = "keep",
    size_overrides: dict[str, SizeOverride] | None = None,
    cover_photo_id: str | None = None,
) -> LayoutResult:
    """Compute placements for all photos using the configured algorithm."""
    _size_ov: dict[str, SizeOverride] = size_overrides or {}

    # Handle cover: place it full-page on page 0, shift remaining to page 1+
    cover_placement: PhotoPlacement | None = None
    page_offset = 0
    working_photos = list(photos)
    if cover_photo_id:
        cover_photo = next((p for p in working_photos if p.id == cover_photo_id), None)
        if cover_photo:
            working_photos = [p for p in working_photos if p.id != cover_photo_id]
            cover_placement = PhotoPlacement(
                photo_id=cover_photo_id,
                page=0,
                x_mm=page_cfg.margin_left_mm,
                y_mm=COVER_TITLE_H_MM,
                w_mm=page_cfg.page_w_mm - page_cfg.margin_left_mm - page_cfg.margin_right_mm,
                h_mm=page_cfg.page_h_mm - COVER_TITLE_H_MM - page_cfg.margin_bottom_mm,
                locked=True,
            )
            page_offset = 1

    if not working_photos:
        placements = [cover_placement] if cover_placement else []
        page_count = 1 if cover_placement else 0
        return LayoutResult(placements=placements, page_count=page_count)

    # Apply relock_behaviour
    if relock_behaviour == "unlock":
        effective_locked: dict[str, PhotoOverride] = {}
    else:
        effective_locked = {k: v for k, v in locked_overrides.items() if k != cover_photo_id}

    if relock_behaviour == "first":
        locked_ids = set(effective_locked)
        locked_photos = [p for p in working_photos if p.id in locked_ids]
        unlocked_photos = [p for p in working_photos if p.id not in locked_ids]
        ordered_photos = locked_photos + unlocked_photos
        effective_locked = {}
    else:
        ordered_photos = list(working_photos)

    layout_fn = {
        "grid": _layout_grid,
        "mosaic": _layout_mosaic,
        "columns": _layout_columns,
    }.get(page_cfg.layout_type, _layout_mosaic)

    result = layout_fn(page_cfg, ordered_photos, effective_locked, _size_ov, page_offset)
    if cover_placement:
        result.placements.insert(0, cover_placement)
        result.page_count = max(result.page_count, 1)
    return result


def _locked_y_ranges(
    locked: dict[str, PhotoOverride], page: int, spacing: float
) -> list[tuple[float, float]]:
    """Return sorted (y_start, y_end) intervals for locked photos on a given page."""
    intervals = [
        (ov.y_mm, ov.y_mm + ov.h_mm + spacing) for ov in locked.values() if ov.page == page
    ]
    intervals.sort()
    return intervals


def _advance_past_locked(y: float, h: float, intervals: list[tuple[float, float]]) -> float:
    """Advance y until [y, y+h] does not overlap any locked interval."""
    changed = True
    while changed:
        changed = False
        for y0, y1 in intervals:
            if y < y1 and y + h > y0:
                y = y1
                changed = True
    return y


def _layout_grid(
    cfg: PageConfig,
    photos: list[PhotoMeta],
    locked: dict[str, PhotoOverride],
    size_overrides: dict[str, SizeOverride] | None = None,
    page_offset: int = 0,
) -> LayoutResult:
    """Regular N-column grid: all photos the same size."""
    _sov = size_overrides or {}
    cols = cfg.columns
    spacing = cfg.spacing_mm
    cell_w = (cfg.usable_w - (cols - 1) * spacing) / cols
    cell_h = cfg.target_row_height_mm

    rows_per_page = int((cfg.usable_h + spacing) / (cell_h + spacing))
    if rows_per_page < 1:
        rows_per_page = 1

    placements: list[PhotoPlacement] = []

    # Place locked photos first at their declared positions
    unlocked = []
    for photo in photos:
        if photo.id in locked:
            ov = locked[photo.id]
            placements.append(
                PhotoPlacement(
                    photo_id=photo.id,
                    page=ov.page,
                    x_mm=ov.x_mm,
                    y_mm=ov.y_mm,
                    w_mm=ov.w_mm,
                    h_mm=ov.h_mm,
                    locked=True,
                )
            )
        else:
            unlocked.append(photo)

    # Flow unlocked photos into grid slots, skipping slots that overlap locked photos
    slot_page = page_offset
    slot_row = 0
    slot_col = 0
    for photo in unlocked:
        # Advance through slots until we find one that doesn't overlap a locked photo
        while True:
            x = cfg.margin_left_mm + slot_col * (cell_w + spacing)
            y = cfg.margin_top_mm + slot_row * (cell_h + spacing)
            intervals = _locked_y_ranges(locked, slot_page, spacing)
            # Check vertical overlap with any locked photo
            overlaps = any(y < y1 and y + cell_h > y0 for y0, y1 in intervals)
            if not overlaps:
                break
            # Advance to next slot
            slot_col += 1
            if slot_col >= cols:
                slot_col = 0
                slot_row += 1
            if slot_row >= rows_per_page:
                slot_row = 0
                slot_page += 1

        ov_size = _sov.get(photo.id)
        placements.append(
            PhotoPlacement(
                photo_id=photo.id,
                page=slot_page,
                x_mm=x,
                y_mm=y,
                w_mm=ov_size.w_mm if ov_size else cell_w,
                h_mm=ov_size.h_mm if ov_size else cell_h,
                locked=False,
            )
        )
        # Advance to next slot
        slot_col += 1
        if slot_col >= cols:
            slot_col = 0
            slot_row += 1
        if slot_row >= rows_per_page:
            slot_row = 0
            slot_page += 1

    page_count = max((p.page for p in placements), default=0) + 1 if placements else 0
    return LayoutResult(placements=placements, page_count=page_count)


def _layout_mosaic(
    cfg: PageConfig,
    photos: list[PhotoMeta],
    locked: dict[str, PhotoOverride],
    size_overrides: dict[str, SizeOverride] | None = None,
    page_offset: int = 0,
) -> LayoutResult:
    """Justified (Flickr-style) layout: rows fill full width, photos keep aspect ratio."""
    _sov = size_overrides or {}
    spacing = cfg.spacing_mm
    target_h = cfg.target_row_height_mm
    usable_w = cfg.usable_w
    usable_h = cfg.usable_h

    placements: list[PhotoPlacement] = []
    page = page_offset
    current_y = cfg.margin_top_mm

    # Place locked photos at declared positions
    unlocked = []
    for photo in photos:
        if photo.id in locked:
            ov = locked[photo.id]
            placements.append(
                PhotoPlacement(
                    photo_id=photo.id,
                    page=ov.page,
                    x_mm=ov.x_mm,
                    y_mm=ov.y_mm,
                    w_mm=ov.w_mm,
                    h_mm=ov.h_mm,
                    locked=True,
                )
            )
        else:
            unlocked.append(photo)

    # Group unlocked photos into rows
    i = 0
    while i < len(unlocked):
        photo = unlocked[i]

        # Size-overridden photo: forms its own row at forced dimensions
        if photo.id in _sov:
            ov_size = _sov[photo.id]
            row_h = ov_size.h_mm
            row_w = min(ov_size.w_mm, usable_w)
            if current_y + row_h > cfg.margin_top_mm + usable_h and current_y > cfg.margin_top_mm:
                page += 1
                current_y = cfg.margin_top_mm
            intervals = _locked_y_ranges(locked, page, spacing)
            current_y = _advance_past_locked(current_y, row_h, intervals)
            if current_y + row_h > cfg.margin_top_mm + usable_h and current_y > cfg.margin_top_mm:
                page += 1
                current_y = cfg.margin_top_mm
                intervals = _locked_y_ranges(locked, page, spacing)
                current_y = _advance_past_locked(current_y, row_h, intervals)
            placements.append(
                PhotoPlacement(
                    photo_id=photo.id,
                    page=page,
                    x_mm=cfg.margin_left_mm,
                    y_mm=current_y,
                    w_mm=row_w,
                    h_mm=row_h,
                    locked=False,
                )
            )
            current_y += row_h + spacing
            i += 1
            continue

        # Normal row-building for unlocked photos
        row_photos: list[PhotoMeta] = []
        row_width = 0.0
        j = i
        while j < len(unlocked):
            p = unlocked[j]
            if p.id in _sov:
                break  # size-overridden photos always form their own row
            w_at_target = p.aspect * target_h
            if row_photos and row_width + spacing + w_at_target > usable_w * 1.2:
                break
            row_photos.append(p)
            row_width += w_at_target + (spacing if row_photos else 0)
            j += 1

        if not row_photos:
            row_photos = [unlocked[i]]
            j = i + 1

        # Scale row to fill usable width
        total_spacing = spacing * (len(row_photos) - 1)
        total_aspect = sum(p.aspect for p in row_photos)
        row_h = (usable_w - total_spacing) / total_aspect if total_aspect > 0 else target_h

        # Check if row fits on current page
        if current_y + row_h > cfg.margin_top_mm + usable_h and current_y > cfg.margin_top_mm:
            page += 1
            current_y = cfg.margin_top_mm

        # Advance past any locked photo that occupies this y-range
        intervals = _locked_y_ranges(locked, page, spacing)
        current_y = _advance_past_locked(current_y, row_h, intervals)
        # If advancing pushed us off the page, move to next page
        if current_y + row_h > cfg.margin_top_mm + usable_h and current_y > cfg.margin_top_mm:
            page += 1
            current_y = cfg.margin_top_mm
            intervals = _locked_y_ranges(locked, page, spacing)
            current_y = _advance_past_locked(current_y, row_h, intervals)

        current_x = cfg.margin_left_mm
        for photo in row_photos:
            w = photo.aspect * row_h
            placements.append(
                PhotoPlacement(
                    photo_id=photo.id,
                    page=page,
                    x_mm=current_x,
                    y_mm=current_y,
                    w_mm=w,
                    h_mm=row_h,
                    locked=False,
                )
            )
            current_x += w + spacing

        current_y += row_h + spacing
        i = j

    page_count = max((p.page for p in placements), default=0) + 1 if placements else 0
    return LayoutResult(placements=placements, page_count=page_count)


def _layout_columns(
    cfg: PageConfig,
    photos: list[PhotoMeta],
    locked: dict[str, PhotoOverride],
    size_overrides: dict[str, SizeOverride] | None = None,
    page_offset: int = 0,
) -> LayoutResult:
    """Masonry (Pinterest-style) layout: each photo goes in the shortest column."""
    _sov = size_overrides or {}
    cols = cfg.columns
    spacing = cfg.spacing_mm
    col_w = (cfg.usable_w - (cols - 1) * spacing) / cols
    usable_h = cfg.usable_h

    placements: list[PhotoPlacement] = []
    col_heights = [cfg.margin_top_mm] * cols
    col_pages = [page_offset] * cols

    # Place locked photos at declared positions
    unlocked = []
    for photo in photos:
        if photo.id in locked:
            ov = locked[photo.id]
            placements.append(
                PhotoPlacement(
                    photo_id=photo.id,
                    page=ov.page,
                    x_mm=ov.x_mm,
                    y_mm=ov.y_mm,
                    w_mm=ov.w_mm,
                    h_mm=ov.h_mm,
                    locked=True,
                )
            )
        else:
            unlocked.append(photo)

    # Pre-advance column heights to account for locked photos already placed
    for ov in locked.values():
        # Determine which column index this locked photo belongs to
        c = round((ov.x_mm - cfg.margin_left_mm) / (col_w + spacing))
        c = max(0, min(cols - 1, c))
        if ov.page == col_pages[c]:
            bottom = ov.y_mm + ov.h_mm + spacing
            if bottom > col_heights[c]:
                col_heights[c] = bottom

    for photo in unlocked:
        ov_size = _sov.get(photo.id)
        photo_h = ov_size.h_mm if ov_size else cfg.target_row_height_mm

        # Find shortest column on earliest page
        best_col = min(
            range(cols),
            key=lambda c: (col_pages[c], col_heights[c]),
        )

        page = col_pages[best_col]
        y = col_heights[best_col]

        # Check if photo fits on current page
        if y + photo_h > cfg.margin_top_mm + usable_h and y > cfg.margin_top_mm:
            col_pages[best_col] += 1
            col_heights[best_col] = cfg.margin_top_mm
            page = col_pages[best_col]
            y = cfg.margin_top_mm

        # Advance past any locked photo occupying this column's y-range
        col_x = cfg.margin_left_mm + best_col * (col_w + spacing)
        col_intervals = [
            (ov.y_mm, ov.y_mm + ov.h_mm + spacing)
            for ov in locked.values()
            if ov.page == page and abs(ov.x_mm - col_x) < col_w
        ]
        col_intervals.sort()
        y = _advance_past_locked(y, photo_h, col_intervals)
        if y + photo_h > cfg.margin_top_mm + usable_h and y > cfg.margin_top_mm:
            col_pages[best_col] += 1
            col_heights[best_col] = cfg.margin_top_mm
            page = col_pages[best_col]
            y = cfg.margin_top_mm

        x = cfg.margin_left_mm + best_col * (col_w + spacing)
        placements.append(
            PhotoPlacement(
                photo_id=photo.id,
                page=page,
                x_mm=x,
                y_mm=y,
                w_mm=col_w,
                h_mm=photo_h,
                locked=False,
            )
        )
        col_heights[best_col] = y + photo_h + spacing

    page_count = max((p.page for p in placements), default=0) + 1 if placements else 0
    return LayoutResult(placements=placements, page_count=page_count)
