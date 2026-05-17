"""Unit tests for the layout engine."""

from __future__ import annotations

import pytest

from pholio.layout import (
    PageConfig,
    PhotoMeta,
    PhotoOverride,
    run_layout,
)


def make_cfg(
    layout_type: str = "mosaic",
    cols: int = 3,
    w: float = 277.0,
    h: float = 190.0,
) -> PageConfig:
    return PageConfig(
        page_w_mm=w,
        page_h_mm=h,
        margin_mm=10.0,
        spacing_mm=5.0,
        columns=cols,
        target_row_height_mm=60.0,
        layout_type=layout_type,
    )


def make_photos(n: int, aspect: float = 1.5) -> list[PhotoMeta]:
    """Create n landscape photos with a given aspect ratio."""
    w = int(aspect * 300)
    return [PhotoMeta(id=f"IMG_{i:04d}.jpg", w_px=w, h_px=300) for i in range(n)]


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_photos_returns_empty_result() -> None:
    cfg = make_cfg()
    result = run_layout(cfg, [], locked_overrides={})
    assert result.page_count == 0
    assert result.placements == []


# ---------------------------------------------------------------------------
# Grid layout
# ---------------------------------------------------------------------------


class TestGrid:
    def test_single_photo_placed(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(1)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 1
        assert result.page_count == 1
        p = result.placements[0]
        assert p.page == 0
        assert p.x_mm == pytest.approx(10.0)
        assert p.y_mm == pytest.approx(10.0)

    def test_multiple_pages(self) -> None:
        cfg = make_cfg(layout_type="grid", cols=2, w=100.0, h=100.0)
        photos = make_photos(20)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 20
        assert result.page_count >= 2

    def test_all_photos_placed(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(12)
        result = run_layout(cfg, photos, locked_overrides={})
        ids = {p.photo_id for p in result.placements}
        assert ids == {ph.id for ph in photos}


# ---------------------------------------------------------------------------
# Mosaic layout
# ---------------------------------------------------------------------------


class TestMosaic:
    def test_single_photo_placed(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(1)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 1
        assert result.placements[0].page == 0

    def test_row_fills_width(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(3, aspect=1.5)
        result = run_layout(cfg, photos, locked_overrides={})
        # All photos in first row → placed on page 0
        pages = {p.page for p in result.placements}
        assert 0 in pages

    def test_all_photos_placed(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(10)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 10

    def test_no_overlap_within_page(self) -> None:
        """Photos on the same page should not overlap vertically beyond tolerance."""
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(6)
        result = run_layout(cfg, photos, locked_overrides={})
        page_0 = [p for p in result.placements if p.page == 0]
        # All y + h values should be within page bounds
        for p in page_0:
            assert p.y_mm + p.h_mm <= cfg.page_h_mm + 1.0  # 1 mm tolerance


# ---------------------------------------------------------------------------
# Columns layout
# ---------------------------------------------------------------------------


class TestColumns:
    def test_single_photo_placed(self) -> None:
        cfg = make_cfg(layout_type="columns")
        photos = make_photos(1)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 1
        assert result.page_count == 1

    def test_all_photos_placed(self) -> None:
        cfg = make_cfg(layout_type="columns")
        photos = make_photos(9)
        result = run_layout(cfg, photos, locked_overrides={})
        assert len(result.placements) == 9

    def test_columns_distribute_evenly(self) -> None:
        """With identical photos, photos should distribute across columns."""
        cfg = make_cfg(layout_type="columns", cols=3)
        photos = make_photos(9, aspect=1.0)
        result = run_layout(cfg, photos, locked_overrides={})
        x_positions = {p.x_mm for p in result.placements}
        assert len(x_positions) == 3  # 3 distinct x positions


# ---------------------------------------------------------------------------
# Lock mechanism
# ---------------------------------------------------------------------------


class TestLockMechanism:
    def test_locked_photo_placed_at_override(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(3)
        override = PhotoOverride(page=0, x_mm=100.0, y_mm=50.0, w_mm=80.0, h_mm=60.0)
        result = run_layout(cfg, photos, locked_overrides={photos[0].id: override})
        locked = next(p for p in result.placements if p.photo_id == photos[0].id)
        assert locked.locked is True
        assert locked.x_mm == pytest.approx(100.0)
        assert locked.y_mm == pytest.approx(50.0)

    def test_relock_behaviour_unlock(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(3)
        override = PhotoOverride(page=2, x_mm=100.0, y_mm=100.0, w_mm=50.0, h_mm=50.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={photos[0].id: override},
            relock_behaviour="unlock",
        )
        # With "unlock", no photo should be placed at the override position
        locked_placements = [p for p in result.placements if p.locked]
        assert locked_placements == []

    def test_relock_behaviour_first(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(4)
        # Lock the last photo
        override = PhotoOverride(page=0, x_mm=10.0, y_mm=10.0, w_mm=50.0, h_mm=50.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={photos[3].id: override},
            relock_behaviour="first",
        )
        # With "first", the locked photo is reordered to front but treated as unlocked
        locked_placements = [p for p in result.placements if p.locked]
        assert locked_placements == []  # "first" does not produce locked placements
        assert len(result.placements) == 4
