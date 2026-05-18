"""PDF generation from a LayoutResult using fpdf2."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fpdf import FPDF
from PIL import Image, ImageOps

from pholio.layout import LayoutResult


class _AlbumPDF(FPDF):
    """FPDF subclass that renders a background fill (header) and an optional
    footer watermark on every page via the official fpdf2 hooks."""

    def __init__(
        self,
        watermark: str = "",
        page_bg: tuple[int, int, int] = (255, 255, 255),
        cover_bg: tuple[int, int, int] | None = None,
        unit: str = "mm",
        format: str | tuple[float, float] = "A4",
    ) -> None:
        super().__init__(unit=unit, format=format)
        self._watermark = watermark
        self._page_bg = page_bg
        self._cover_bg = cover_bg  # None → same as page_bg for every page

    def header(self) -> None:
        bg = self._cover_bg if (self.page == 1 and self._cover_bg is not None) else self._page_bg
        r, g, b = bg
        self.set_fill_color(r, g, b)
        self.rect(0, 0, self.w, self.h, "F")

    def footer(self) -> None:
        if not self._watermark:
            return
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(170, 170, 170)
        wm_w = self.get_string_width(self._watermark)
        x = self.w - wm_w - 4
        # y = top of text baseline; 9 pt ≈ 3.2 mm, keep 3 mm clearance
        y = self.h - 6.5
        self.text(x, y, self._watermark)
        self.set_text_color(0, 0, 0)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a '#rrggbb' hex string to an (r, g, b) integer tuple."""
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


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


def _contain_in_slot(
    img: Image.Image, slot_w_mm: float, slot_h_mm: float
) -> tuple[float, float, float, float]:
    """Compute the image rect (x_offset, y_offset, img_w, img_h) to contain the image
    inside the slot without cropping (object-fit: contain, centred)."""
    src_w, src_h = img.size
    img_aspect = src_w / src_h
    slot_aspect = slot_w_mm / slot_h_mm
    if img_aspect > slot_aspect:
        img_w_mm = slot_w_mm
        img_h_mm = slot_w_mm / img_aspect
    else:
        img_h_mm = slot_h_mm
        img_w_mm = slot_h_mm * img_aspect
    x_offset = (slot_w_mm - img_w_mm) / 2
    y_offset = (slot_h_mm - img_h_mm) / 2
    return x_offset, y_offset, img_w_mm, img_h_mm


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
    page_bg_color: str = "#ffffff",
    cover_bg_color: str | None = None,
    cover_photo_id: str | None = None,
    text_blocks: list[dict[str, Any]] | None = None,
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
    pdf = _AlbumPDF(
        watermark=watermark_text or "",
        page_bg=_hex_to_rgb(page_bg_color),
        cover_bg=_hex_to_rgb(cover_bg_color) if cover_bg_color else None,
        unit="mm",
        format=(page_w_mm, page_h_mm),
    )
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

            if placement.photo_id == cover_photo_id:
                # Contain mode: no crop, centred in slot
                x_off, y_off, img_w_mm, img_h_mm = _contain_in_slot(
                    rgb, placement.w_mm, placement.h_mm
                )
                tw = max(1, int(round(img_w_mm / 25.4 * target_dpi)))
                th = max(1, int(round(img_h_mm / 25.4 * target_dpi)))
                src_w, src_h = rgb.size
                if src_w > tw or src_h > th:
                    to_place = rgb.resize((tw, th), Image.Resampling.LANCZOS)
                else:
                    to_place = rgb
                place_x = placement.x_mm + x_off
                place_y = placement.y_mm + y_off
                place_w = img_w_mm
                place_h = img_h_mm
            else:
                # Cover (crop) mode: default behaviour
                cropped = _crop_to_aspect(rgb, placement.w_mm, placement.h_mm)
                src_w, src_h = cropped.size
                if src_w > target_w_px or src_h > target_h_px:
                    to_place = cropped.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
                else:
                    to_place = cropped
                place_x = placement.x_mm
                place_y = placement.y_mm
                place_w = placement.w_mm
                place_h = placement.h_mm

            buf = io.BytesIO()
            to_place.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
            buf.seek(0)

        # fpdf2 pages are 1-indexed
        pdf.page = placement.page + 1
        pdf.image(buf, x=place_x, y=place_y, w=place_w, h=place_h)

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

    # Render text blocks
    for block in text_blocks or []:
        pg = int(block.get("page", 0)) + 1
        if pg < 1 or pg > layout_result.page_count:
            continue
        pdf.page = pg
        style = ""
        if block.get("bold"):
            style += "B"
        if block.get("italic"):
            style += "I"
        font_size = float(block.get("font_size", 24))
        pdf.set_font("Helvetica", style, font_size)
        r, g, b = _hex_to_rgb(str(block.get("font_color", "#000000")))
        pdf.set_text_color(r, g, b)
        line_h = font_size * 0.352778 * 1.2  # pt → mm with 1.2 line spacing
        pdf.set_xy(float(block["x_mm"]), float(block["y_mm"]))
        pdf.multi_cell(
            float(block["w_mm"]),
            line_h,
            str(block.get("text", "")),
            align=str(block.get("align", "C")),
            border=0,
        )
        pdf.set_text_color(0, 0, 0)

    return bytes(pdf.output())
