"""Unit tests for PDF export."""

from __future__ import annotations

import contextlib
import zlib
from pathlib import Path

import pytest
from PIL import Image

from pholio.layout import LayoutResult, PhotoPlacement


def _decompress_streams(pdf_bytes: bytes) -> list[bytes]:
    """Return all successfully decompressed zlib streams found in a PDF byte string."""
    streams: list[bytes] = []
    i = 0
    while i < len(pdf_bytes) - 6:
        if pdf_bytes[i : i + 1] == b"x" and pdf_bytes[i + 1 : i + 2] in (
            b"\x9c",
            b"\xda",
            b"\x01",
        ):
            for size in (512, 1024, 2048, 4096, 8192, 16384, 32768):
                with contextlib.suppress(zlib.error):
                    streams.append(zlib.decompress(pdf_bytes[i : i + size]))
                    break
        i += 1
    return streams


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

    def test_watermark_on_every_page(self, tmp_path: Path) -> None:
        """Watermark text must appear in the content stream of every page."""
        from pholio.pdf_export import generate_pdf

        wm = "MYMARK"
        page_count = 3
        result = LayoutResult(placements=[], page_count=page_count)
        pdf_bytes = generate_pdf(
            result, tmp_path, page_w_mm=297.0, page_h_mm=210.0, watermark_text=wm
        )
        assert pdf_bytes[:4] == b"%PDF"

        # Decompress all zlib streams and count occurrences of the watermark
        wm_bytes = wm.encode("latin-1")
        streams = _decompress_streams(pdf_bytes)
        occurrences = sum(wm_bytes in s for s in streams)

        assert occurrences >= page_count, (
            f"Watermark found in {occurrences} stream(s), expected at least {page_count}"
        )

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

    def test_page_bg_color_applied(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=2)
        pdf_colored = generate_pdf(
            result, tmp_path, page_w_mm=210.0, page_h_mm=297.0, page_bg_color="#1a2b3c"
        )
        pdf_default = generate_pdf(
            result, tmp_path, page_w_mm=210.0, page_h_mm=297.0, page_bg_color="#ffffff"
        )
        assert pdf_colored[:4] == b"%PDF"
        # A non-white background must produce different PDF content than white
        assert pdf_colored != pdf_default

    def test_cover_bg_color_different_from_pages(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=3)
        pdf_with_cover = generate_pdf(
            result,
            tmp_path,
            page_w_mm=210.0,
            page_h_mm=297.0,
            page_bg_color="#ffffff",
            cover_bg_color="#111111",
        )
        pdf_uniform = generate_pdf(
            result, tmp_path, page_w_mm=210.0, page_h_mm=297.0, page_bg_color="#ffffff"
        )
        assert pdf_with_cover[:4] == b"%PDF"
        # A distinct cover colour must change the PDF content
        assert pdf_with_cover != pdf_uniform

    def test_cover_photo_id_contain_no_crop(self, tmp_path: Path) -> None:
        from pholio.pdf_export import _contain_in_slot, generate_pdf

        # 600x400 = landscape 3:2 aspect ratio
        img = Image.new("RGB", (600, 400), color=(80, 120, 160))
        img.save(tmp_path / "COVER.jpg", format="JPEG")
        placement = PhotoPlacement(
            photo_id="COVER.jpg", page=0, x_mm=0.0, y_mm=0.0, w_mm=210.0, h_mm=297.0
        )
        result = LayoutResult(placements=[placement], page_count=1)
        pdf_bytes = generate_pdf(
            result, tmp_path, page_w_mm=210.0, page_h_mm=297.0, cover_photo_id="COVER.jpg"
        )
        assert pdf_bytes[:4] == b"%PDF"

        # _contain_in_slot: portrait slot (210x297), landscape image (3:2)
        # → width-constrained: img_w=210, img_h=210/1.5=140, y_off=(297-140)/2=78.5
        x_off, y_off, img_w, img_h = _contain_in_slot(img, 210.0, 297.0)
        assert img_w == pytest.approx(210.0, rel=1e-3)
        assert img_h == pytest.approx(140.0, rel=1e-3)
        assert x_off == pytest.approx(0.0, abs=1e-3)
        assert y_off == pytest.approx(78.5, rel=1e-2)

    def test_text_blocks_in_pdf(self, tmp_path: Path) -> None:
        from pholio.pdf_export import generate_pdf

        result = LayoutResult(placements=[], page_count=2)
        blocks = [
            {
                "id": "tb1",
                "page": 0,
                "x_mm": 20.0,
                "y_mm": 20.0,
                "w_mm": 100.0,
                "h_mm": 30.0,
                "text": "Titre de l'album",
                "font_size": 24.0,
                "font_color": "#1a1a1a",
                "align": "C",
                "bold": True,
                "italic": False,
            },
            {
                "id": "tb2",
                "page": 1,
                "x_mm": 10.0,
                "y_mm": 10.0,
                "w_mm": 80.0,
                "h_mm": 20.0,
                "text": "Description",
                "font_size": 12.0,
                "font_color": "#444444",
                "align": "L",
                "bold": False,
                "italic": True,
            },
        ]
        pdf_bytes = generate_pdf(
            result, tmp_path, page_w_mm=210.0, page_h_mm=297.0, text_blocks=blocks
        )
        assert pdf_bytes[:4] == b"%PDF"
        # Both block texts must appear in at least one decompressed content stream
        streams = _decompress_streams(pdf_bytes)
        assert any(b"Titre de l'album" in s for s in streams)
        assert any(b"Description" in s for s in streams)
