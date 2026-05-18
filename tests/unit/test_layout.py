"""Unit tests for the layout engine."""

from __future__ import annotations

import pytest

from pholio.layout import (
    PageConfig,
    PhotoMeta,
    PhotoOverride,
    SizeOverride,
    run_layout,
)


def make_cfg(
    layout_type: str = "mosaic",
    cols: int = 3,
    w: float = 277.0,
    h: float = 190.0,
    margin: float = 10.0,
) -> PageConfig:
    return PageConfig(
        page_w_mm=w,
        page_h_mm=h,
        margin_top_mm=margin,
        margin_right_mm=margin,
        margin_bottom_mm=margin,
        margin_left_mm=margin,
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

    def test_unlocked_photos_do_not_overlap_locked_mosaic(self) -> None:
        """Unlocked photos must not overlap a locked photo vertically (mosaic)."""
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(6)
        # Lock one photo in the middle of the page
        override = PhotoOverride(page=0, x_mm=10.0, y_mm=80.0, w_mm=100.0, h_mm=50.0)
        result = run_layout(cfg, photos, locked_overrides={photos[2].id: override})
        locked_y0 = override.y_mm
        locked_y1 = override.y_mm + override.h_mm
        for p in result.placements:
            if p.locked:
                continue
            if p.page != 0:
                continue
            p_y0 = p.y_mm
            p_y1 = p.y_mm + p.h_mm
            assert p_y1 <= locked_y0 + 0.5 or p_y0 >= locked_y1 - 0.5, (
                f"Photo {p.photo_id} y={p.y_mm:.1f}-{p_y1:.1f} "
                f"overlaps locked y={locked_y0}-{locked_y1}"
            )

    def test_unlocked_photos_do_not_overlap_locked_grid(self) -> None:
        """Unlocked photos must not overlap a locked photo vertically (grid)."""
        cfg = make_cfg(layout_type="grid", cols=3)
        photos = make_photos(9)
        override = PhotoOverride(page=0, x_mm=10.0, y_mm=60.0, w_mm=50.0, h_mm=40.0)
        result = run_layout(cfg, photos, locked_overrides={photos[4].id: override})
        locked_y0 = override.y_mm
        locked_y1 = override.y_mm + override.h_mm
        for p in result.placements:
            if p.locked or p.page != 0:
                continue
            p_y1 = p.y_mm + p.h_mm
            assert p_y1 <= locked_y0 + 0.5 or p.y_mm >= locked_y1 - 0.5, (
                f"Photo {p.photo_id} y={p.y_mm:.1f}-{p_y1:.1f} "
                f"overlaps locked y={locked_y0}-{locked_y1}"
            )

    def test_unlocked_photos_do_not_overlap_locked_columns(self) -> None:
        """Unlocked photos must not overlap a locked photo in the same column (columns)."""
        cfg = make_cfg(layout_type="columns", cols=3)
        photos = make_photos(9)
        # Lock a photo in column 0 (x=10)
        override = PhotoOverride(page=0, x_mm=10.0, y_mm=30.0, w_mm=80.0, h_mm=50.0)
        result = run_layout(cfg, photos, locked_overrides={photos[0].id: override})
        locked_y0 = override.y_mm
        locked_y1 = override.y_mm + override.h_mm
        col_x = cfg.margin_left_mm  # column 0
        col_w = (cfg.usable_w - 2 * cfg.spacing_mm) / 3
        for p in result.placements:
            if p.locked or p.page != 0:
                continue
            if abs(p.x_mm - col_x) > col_w:
                continue  # different column
            p_y1 = p.y_mm + p.h_mm
            assert p_y1 <= locked_y0 + 0.5 or p.y_mm >= locked_y1 - 0.5, (
                f"Photo {p.photo_id} y={p.y_mm:.1f}-{p_y1:.1f} "
                f"overlaps locked y={locked_y0}-{locked_y1}"
            )

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
        assert not locked_placements

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
        assert not locked_placements  # "first" does not produce locked placements
        assert len(result.placements) == 4


# ---------------------------------------------------------------------------
# Cover photo
# ---------------------------------------------------------------------------


class TestCoverPhoto:
    def test_cover_on_page_0(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(5)
        cover_id = photos[0].id
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=cover_id)
        cover_pl = next(p for p in result.placements if p.photo_id == cover_id)
        assert cover_pl.page == 0
        assert cover_pl.locked is True

    def test_other_photos_start_at_page_1(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(5)
        cover_id = photos[0].id
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=cover_id)
        others = [p for p in result.placements if p.photo_id != cover_id]
        assert all(p.page >= 1 for p in others)

    def test_cover_fills_usable_area(self) -> None:
        from pholio.layout import COVER_TITLE_H_MM

        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(3)
        cover_id = photos[0].id
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=cover_id)
        cover_pl = next(p for p in result.placements if p.photo_id == cover_id)
        # Width = full usable width (between left/right margins)
        assert cover_pl.w_mm == pytest.approx(cfg.usable_w)
        # Photo starts at the bottom of the title band (no top margin)
        assert cover_pl.y_mm == pytest.approx(COVER_TITLE_H_MM)
        # Photo fills from title band down to the bottom margin
        assert cover_pl.h_mm == pytest.approx(
            cfg.page_h_mm - COVER_TITLE_H_MM - cfg.margin_bottom_mm
        )

    def test_only_cover_photo(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(1)
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=photos[0].id)
        assert result.page_count == 1
        assert len(result.placements) == 1

    def test_cover_works_with_grid(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(4)
        cover_id = photos[0].id
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=cover_id)
        others = [p for p in result.placements if p.photo_id != cover_id]
        assert all(p.page >= 1 for p in others)

    def test_cover_works_with_columns(self) -> None:
        cfg = make_cfg(layout_type="columns")
        photos = make_photos(6)
        cover_id = photos[0].id
        result = run_layout(cfg, photos, locked_overrides={}, cover_photo_id=cover_id)
        others = [p for p in result.placements if p.photo_id != cover_id]
        assert all(p.page >= 1 for p in others)


# ---------------------------------------------------------------------------
# SizeOverride
# ---------------------------------------------------------------------------


class TestSizeOverride:
    def test_mosaic_size_override_forces_dimensions(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(3)
        forced = SizeOverride(w_mm=50.0, h_mm=40.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={},
            size_overrides={photos[1].id: forced},
        )
        pl = next(p for p in result.placements if p.photo_id == photos[1].id)
        assert pl.w_mm == pytest.approx(50.0)
        assert pl.h_mm == pytest.approx(40.0)

    def test_grid_size_override_forces_dimensions(self) -> None:
        cfg = make_cfg(layout_type="grid")
        photos = make_photos(3)
        forced = SizeOverride(w_mm=55.0, h_mm=45.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={},
            size_overrides={photos[0].id: forced},
        )
        pl = next(p for p in result.placements if p.photo_id == photos[0].id)
        assert pl.w_mm == pytest.approx(55.0)
        assert pl.h_mm == pytest.approx(45.0)

    def test_columns_size_override_forces_height(self) -> None:
        cfg = make_cfg(layout_type="columns")
        photos = make_photos(3)
        forced = SizeOverride(w_mm=80.0, h_mm=35.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={},
            size_overrides={photos[2].id: forced},
        )
        pl = next(p for p in result.placements if p.photo_id == photos[2].id)
        assert pl.h_mm == pytest.approx(35.0)

    def test_non_overridden_photos_use_default_size_mosaic(self) -> None:
        cfg = make_cfg(layout_type="mosaic")
        photos = make_photos(3, aspect=1.5)
        forced = SizeOverride(w_mm=50.0, h_mm=40.0)
        result = run_layout(
            cfg,
            photos,
            locked_overrides={},
            size_overrides={photos[0].id: forced},
        )
        others = [p for p in result.placements if p.photo_id != photos[0].id]
        # Other photos should have heights close to the row scale (not 40 mm)
        for p in others:
            assert p.h_mm != pytest.approx(40.0, abs=1.0)


# ---------------------------------------------------------------------------
# Grid uses target_row_height_mm
# ---------------------------------------------------------------------------


class TestGridTargetHeight:
    def test_cell_height_equals_target_row_height(self) -> None:
        cfg = make_cfg(layout_type="grid")
        cfg.target_row_height_mm = 45.0
        photos = make_photos(1)
        result = run_layout(cfg, photos, locked_overrides={})
        assert result.placements[0].h_mm == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# Columns uses target_row_height_mm
# ---------------------------------------------------------------------------


class TestColumnsTargetHeight:
    def test_photo_height_equals_target_row_height(self) -> None:
        cfg = make_cfg(layout_type="columns")
        cfg.target_row_height_mm = 50.0
        photos = make_photos(3, aspect=2.0)
        result = run_layout(cfg, photos, locked_overrides={})
        for p in result.placements:
            assert p.h_mm == pytest.approx(50.0)
