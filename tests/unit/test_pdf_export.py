"""Unit tests for PDF export."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pholio.layout import LayoutResult, PhotoPlacement


class TestGeneratePdf:
    def test_empty_layout_returns_bytes(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=1)
        pdf_bytes = generate_pdf(result, tmp_path, page_w_mm=297.0, page_h_mm=210.0)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:4] == b"%PDF"

    def test_single_photo_exported(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        # Create a test JPEG
        img = Image.new("RGB", (400, 300), color=(100, 150, 200))
        img.save(tmp_path / "IMG_0001.jpg", format="JPEG")

        placement = PhotoPlacement(
            photo_id="IMG_0001.jpg",
            page=0,
            x_mm=10.0,
            y_mm=10.0,
            w_mm=80.0,
            h_mm=60.0,
        )
        result = LayoutResult(placements=[placement], page_count=1)
        pdf_bytes = generate_pdf(result, tmp_path, page_w_mm=297.0, page_h_mm=210.0)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1000  # Should contain image data

    def test_missing_photo_skipped(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        placement = PhotoPlacement(
            photo_id="MISSING.jpg",
            page=0,
            x_mm=10.0,
            y_mm=10.0,
            w_mm=80.0,
            h_mm=60.0,
        )
        result = LayoutResult(placements=[placement], page_count=1)
        # Should not raise, just skip the missing photo
        pdf_bytes = generate_pdf(result, tmp_path, page_w_mm=297.0, page_h_mm=210.0)
        assert pdf_bytes[:4] == b"%PDF"

    def test_watermark_renders_without_error(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=2)
        pdf_bytes = generate_pdf(
            result, tmp_path, page_w_mm=297.0, page_h_mm=210.0, watermark_text="© Test 2025"
        )
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 0

    def test_watermark_empty_string_ignored(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=1)
        pdf_no_wm = generate_pdf(result, tmp_path, page_w_mm=297.0, page_h_mm=210.0)
        pdf_empty_wm = generate_pdf(
            result, tmp_path, page_w_mm=297.0, page_h_mm=210.0, watermark_text=""
        )
        # No watermark vs empty watermark — both should produce valid PDFs
        assert pdf_no_wm[:4] == b"%PDF"
        assert pdf_empty_wm[:4] == b"%PDF"

    def test_caption_renders_without_error(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        img = Image.new("RGB", (400, 300), color=(100, 150, 200))
        img.save(tmp_path / "IMG_CAP.jpg", format="JPEG")

        placement = PhotoPlacement(
            photo_id="IMG_CAP.jpg",
            page=0,
            x_mm=10.0,
            y_mm=10.0,
            w_mm=80.0,
            h_mm=60.0,
        )
        result = LayoutResult(placements=[placement], page_count=1)
        pdf_bytes = generate_pdf(
            result,
            tmp_path,
            page_w_mm=297.0,
            page_h_mm=210.0,
            captions={"IMG_CAP.jpg": "Légende de test"},
        )
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1000

    def test_caption_missing_photo_id_ignored(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=1)
        # Captions for photos not in the layout are silently ignored
        pdf_bytes = generate_pdf(
            result,
            tmp_path,
            page_w_mm=297.0,
            page_h_mm=210.0,
            captions={"ABSENT.jpg": "This photo has no placement"},
        )
        assert pdf_bytes[:4] == b"%PDF"
