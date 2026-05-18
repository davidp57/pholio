"""PDF generation from a LayoutResult using fpdf2."""

from __future__ import annotations

import io
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageOps

from pholio.layout import LayoutResult


def _crop_to_aspect(img: Image.Image, target_w_mm: float, target_h_mm: float) -> Image.Image:
    """Centered crop to match the target aspect ratio (like CSS object-fit: cover)."""
    target_aspect = target_w_mm / target_h_mm
    src_w, src_h = img.size
    src_aspect = src_w / src_h

    if abs(src_aspect - target_aspect) < 0.005:
        return img

    if src_aspect > target_aspect:
        # Image wider than target: crop left and right
        new_w = int(round(src_h * target_aspect))
        left = (src_w - new_w) // 2
        return img.crop((left, 0, left + new_w, src_h))
    else:
        # Image taller than target: crop top and bottom
        new_h = int(round(src_w / target_aspect))
        top = (src_h - new_h) // 2
        return img.crop((0, top, src_w, top + new_h))


def generate_pdf(
    layout_result: LayoutResult,
    album_path: Path,
    page_w_mm: float,
    page_h_mm: float,
    jpeg_quality: int = 85,
    target_dpi: int = 150,
    cover_title: str | None = None,
    watermark_text: str | None = None,
    captions: dict[str, str] | None = None,
) -> bytes:
    """Generate a PDF from a LayoutResult.

    Args:
        layout_result: Computed photo placements.
        album_path: Path to the album folder containing source images.
        page_w_mm: Page width in mm.
        page_h_mm: Page height in mm.
        jpeg_quality: JPEG compression quality for embedded images (1-95).
        target_dpi: Target resolution for embedded images (pixels per inch).
            150 is a good balance between quality and file size.
        cover_title: Optional title rendered on the cover page.

    Returns:
        PDF file content as bytes.
    """
    pdf = FPDF(unit="mm", format=(page_w_mm, page_h_mm))
    pdf.set_auto_page_break(auto=False)

    # Create pages
    for _ in range(layout_result.page_count):
        pdf.add_page()

    # Place images
    resolved_album = album_path.resolve()
    for placement in layout_result.placements:
        image_path = (album_path / placement.photo_id).resolve()
        if not image_path.is_relative_to(resolved_album):
            continue
        if not image_path.exists():
            continue

        # Target pixel dimensions at the requested DPI
        target_w_px = max(1, int(round(placement.w_mm / 25.4 * target_dpi)))
        target_h_px = max(1, int(round(placement.h_mm / 25.4 * target_dpi)))

        with Image.open(image_path) as raw:
            oriented = ImageOps.exif_transpose(raw)
            rgb: Image.Image = (
                oriented.convert("RGB") if oriented.mode not in ("RGB", "L") else oriented
            )
            # Crop to target aspect ratio (matches browser object-fit: cover)
            cropped = _crop_to_aspect(rgb, placement.w_mm, placement.h_mm)
            # Downscale to target DPI — never upscale
            src_w, src_h = cropped.size
            if src_w > target_w_px or src_h > target_h_px:
                resized = cropped.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
            else:
                resized = cropped

            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
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

        # Render caption overlay if present
        if captions:
            caption_text = captions.get(placement.photo_id, "")
            if caption_text:
                _cap_h = 6.5
                pdf.set_fill_color(20, 20, 20)
                pdf.rect(
                    placement.x_mm,
                    placement.y_mm + placement.h_mm - _cap_h,
                    placement.w_mm,
                    _cap_h,
                    "F",
                )
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(240, 240, 240)
                pdf.set_xy(placement.x_mm, placement.y_mm + placement.h_mm - _cap_h)
                pdf.cell(placement.w_mm, _cap_h, caption_text, align="C")
                pdf.set_text_color(0, 0, 0)

    # Render cover title on page 1 (first page), at the top
    if cover_title and layout_result.page_count > 0:
        from pholio.layout import COVER_TITLE_H_MM

        title_h = COVER_TITLE_H_MM
        pdf.page = 1
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(0.0, 0.0, page_w_mm, title_h, "F")
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0.0, 2.0)
        pdf.cell(page_w_mm, title_h - 4.0, cover_title, align="C")

    # Render watermark on every page (bottom-right, light gray italic)
    if watermark_text:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(170, 170, 170)
        for pg in range(1, layout_result.page_count + 1):
            pdf.page = pg
            pdf.set_xy(0, page_h_mm - 7)
            pdf.cell(page_w_mm - 4, 7, watermark_text, align="R")
        pdf.set_text_color(0, 0, 0)

    return bytes(pdf.output())
