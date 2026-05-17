"""PDF generation from a LayoutResult using fpdf2."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageOps

from pholio.layout import LayoutResult


def generate_pdf(
    layout_result: LayoutResult,
    album_path: Path,
    page_w_mm: float,
    page_h_mm: float,
    jpeg_quality: int = 90,
) -> bytes:
    """Generate a PDF from a LayoutResult.

    Args:
        layout_result: Computed photo placements.
        album_path: Path to the album folder containing source images.
        page_w_mm: Page width in mm.
        page_h_mm: Page height in mm.
        jpeg_quality: JPEG compression quality for embedded images (1-95).

    Returns:
        PDF file content as bytes.
    """
    pdf = FPDF(unit="mm", format=(page_w_mm, page_h_mm))
    pdf.set_auto_page_break(auto=False)

    # Create pages
    for _ in range(layout_result.page_count):
        pdf.add_page()

    # Place images
    for placement in layout_result.placements:
        image_path = album_path / placement.photo_id
        if not image_path.exists():
            continue

        # Load and correct EXIF orientation
        with Image.open(image_path) as raw:
            oriented = ImageOps.exif_transpose(raw)
            # Convert to RGB for JPEG embedding
            final: Image.Image = (
                oriented.convert("RGB") if oriented.mode not in ("RGB", "L") else oriented
            )

            # Serialize to JPEG in memory
            import io

            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=jpeg_quality)
            buf.seek(0)

        # fpdf2 pages are 1-indexed
        pdf.page = placement.page + 1
        pdf.image(
            buf,
            x=placement.x_mm,
            y=placement.y_mm,
            w=placement.w_mm,
            h=placement.h_mm,
        )

    return bytes(pdf.output())
