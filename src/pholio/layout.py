"""Layout engine: grid, mosaic, and columns algorithms with lock support."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageConfig:
    page_w_mm: float
    page_h_mm: float
    margin_mm: float
    spacing_mm: float
    columns: int = 3
    target_row_height_mm: float = 60.0
    layout_type: str = "mosaic"

    @property
    def usable_w(self) -> float:
        return self.page_w_mm - 2 * self.margin_mm

    @property
    def usable_h(self) -> float:
        return self.page_h_mm - 2 * self.margin_mm


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
) -> LayoutResult:
    """Compute placements for all photos using the configured algorithm.

    Args:
        page_cfg: Page dimensions and layout parameters.
        photos: Ordered list of photos to lay out.
        locked_overrides: Map of photo_id -> PhotoOverride for locked photos.
        relock_behaviour: "keep" | "first" | "unlock"

    Returns:
        LayoutResult with all placements and total page count.
    """
    if not photos:
        return LayoutResult(placements=[], page_count=0)

    # Apply relock_behaviour
    if relock_behaviour == "unlock":
        effective_locked: dict[str, PhotoOverride] = {}
    else:
        effective_locked = locked_overrides

    if relock_behaviour == "first":
        # Reorder locked photos to front, but treat all as unlocked
        locked_ids = set(effective_locked)
        locked_photos = [p for p in photos if p.id in locked_ids]
        unlocked_photos = [p for p in photos if p.id not in locked_ids]
        ordered_photos = locked_photos + unlocked_photos
        effective_locked = {}  # clear locks so they flow freely
    else:
        ordered_photos = list(photos)

    layout_fn = {
        "grid": _layout_grid,
        "mosaic": _layout_mosaic,
        "columns": _layout_columns,
    }.get(page_cfg.layout_type, _layout_mosaic)

    return layout_fn(page_cfg, ordered_photos, effective_locked)


def _layout_grid(
    cfg: PageConfig,
    photos: list[PhotoMeta],
    locked: dict[str, PhotoOverride],
) -> LayoutResult:
    """Regular N-column grid: all photos the same size."""
    cols = cfg.columns
    spacing = cfg.spacing_mm
    cell_w = (cfg.usable_w - (cols - 1) * spacing) / cols
    cell_h = cell_w  # square cells

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

    # Flow unlocked photos into grid slots
    for slot, photo in enumerate(unlocked):
        page = slot // (cols * rows_per_page)
        slot_in_page = slot % (cols * rows_per_page)
        row = slot_in_page // cols
        col = slot_in_page % cols
        x = cfg.margin_mm + col * (cell_w + spacing)
        y = cfg.margin_mm + row * (cell_h + spacing)
        placements.append(
            PhotoPlacement(
                photo_id=photo.id,
                page=page,
                x_mm=x,
                y_mm=y,
                w_mm=cell_w,
                h_mm=cell_h,
                locked=False,
            )
        )

    page_count = max((p.page for p in placements), default=0) + 1 if placements else 0
    return LayoutResult(placements=placements, page_count=page_count)


def _layout_mosaic(
    cfg: PageConfig,
    photos: list[PhotoMeta],
    locked: dict[str, PhotoOverride],
) -> LayoutResult:
    """Justified (Flickr-style) layout: rows fill full width, photos keep aspect ratio."""
    spacing = cfg.spacing_mm
    target_h = cfg.target_row_height_mm
    usable_w = cfg.usable_w
    usable_h = cfg.usable_h

    placements: list[PhotoPlacement] = []
    page = 0
    current_y = cfg.margin_mm

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
        # Accumulate photos for the current row
        row_photos: list[PhotoMeta] = []
        row_width = 0.0
        j = i
        while j < len(unlocked):
            p = unlocked[j]
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
        if current_y + row_h > cfg.margin_mm + usable_h and current_y > cfg.margin_mm:
            page += 1
            current_y = cfg.margin_mm

        current_x = cfg.margin_mm
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
) -> LayoutResult:
    """Masonry (Pinterest-style) layout: each photo goes in the shortest column."""
    cols = cfg.columns
    spacing = cfg.spacing_mm
    col_w = (cfg.usable_w - (cols - 1) * spacing) / cols
    usable_h = cfg.usable_h

    placements: list[PhotoPlacement] = []
    col_heights = [cfg.margin_mm] * cols
    col_pages = [0] * cols

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

    for photo in unlocked:
        photo_h = col_w / photo.aspect if photo.aspect > 0 else col_w

        # Find shortest column on earliest page
        best_col = min(
            range(cols),
            key=lambda c: (col_pages[c], col_heights[c]),
        )

        page = col_pages[best_col]
        y = col_heights[best_col]

        # Check if photo fits on current page
        if y + photo_h > cfg.margin_mm + usable_h and y > cfg.margin_mm:
            col_pages[best_col] += 1
            col_heights[best_col] = cfg.margin_mm
            page = col_pages[best_col]
            y = cfg.margin_mm

        x = cfg.margin_mm + best_col * (col_w + spacing)
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
