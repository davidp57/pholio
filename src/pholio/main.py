"""FastAPI application factory and route definitions."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pholio.config import IMAGES_DIR, THUMBNAILS_DIR
from pholio.image_utils import get_or_create_thumbnail, scan_album
from pholio.layout import (
    LayoutResult,
    PageConfig,
    PhotoMeta,
    PhotoOverride,
    PhotoPlacement,
    SizeOverride,
    run_layout,
)
from pholio.pdf_export import generate_pdf
from pholio.state import load_session, save_session


def _find_static_dir() -> Path:
    """Locate static/ whether running normally or as a PyInstaller frozen exe."""
    if getattr(sys, "frozen", False):
        # PyInstaller: sys._MEIPASS is the extraction/bundle directory
        return Path(sys._MEIPASS) / "static"  # type: ignore[attr-defined]
    return Path(__file__).parent.parent.parent / "static"


_STATIC_DIR = _find_static_dir()
_THUMBNAILS_DIR = Path(THUMBNAILS_DIR).resolve()
_IMAGES_DIR = Path(IMAGES_DIR).resolve()


class LayoutRequest(BaseModel):
    page_w_mm: float = 297.0
    page_h_mm: float = 210.0
    margin_top_mm: float = 10.0
    margin_right_mm: float = 10.0
    margin_bottom_mm: float = 10.0
    margin_left_mm: float = 10.0
    spacing_mm: float = 5.0
    columns: int = 3
    target_row_height_mm: float = 60.0
    layout_type: str = "mosaic"
    relock_behaviour: str = "keep"
    photos: list[dict[str, Any]]
    locked_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    size_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    cover_photo_id: str | None = None


class ExportRequest(BaseModel):
    album_name: str
    page_w_mm: float = 297.0
    page_h_mm: float = 210.0
    jpeg_quality: int = 85
    target_dpi: int = 150
    layout_result: dict[str, Any]
    cover_title: str | None = None
    watermark_text: str | None = None
    captions: dict[str, str] = Field(default_factory=dict)


def create_app() -> FastAPI:
    try:
        _version = _pkg_version("pholio")
    except PackageNotFoundError:
        _version = "dev"
    app = FastAPI(title="Pholio", version=_version)

    # --- Version ---

    @app.get("/api/version")
    async def get_version() -> dict[str, str]:
        try:
            v = _pkg_version("pholio")
        except PackageNotFoundError:
            v = "dev"
        return {"version": v}

    # --- Albums ---

    @app.get("/api/albums")
    async def list_albums() -> list[dict[str, Any]]:
        images_dir = Path(IMAGES_DIR)
        if not images_dir.exists():
            return []
        return [
            {"name": d.name, "path": str(d)} for d in sorted(images_dir.iterdir()) if d.is_dir()
        ]

    @app.get("/api/albums/{album_name}/photos")
    async def list_photos(album_name: str) -> list[dict[str, Any]]:
        album_path = Path(IMAGES_DIR) / album_name
        if not album_path.exists():
            return []
        photos = scan_album(album_path)
        for photo in photos:
            thumb = get_or_create_thumbnail(Path(str(photo["path"])), album_name)
            rel = thumb.resolve().relative_to(_THUMBNAILS_DIR).as_posix()
            photo["thumb_url"] = f"/thumbnails/{rel}"
            h = photo["h_px"]
            photo["aspect"] = (photo["w_px"] / h) if h else 1.0  # type: ignore[operator]
        return photos

    # --- Thumbnails ---

    @app.get("/thumbnails/{rest_of_path:path}")
    async def serve_thumbnail(rest_of_path: str) -> FileResponse:
        thumb_path = (_THUMBNAILS_DIR / rest_of_path).resolve()
        if not thumb_path.is_relative_to(_THUMBNAILS_DIR):
            raise HTTPException(status_code=404)
        return FileResponse(str(thumb_path), media_type="image/webp")

    # --- Layout ---

    @app.post("/api/layout/compute")
    async def compute_layout(req: LayoutRequest) -> dict[str, Any]:
        page_cfg = PageConfig(
            page_w_mm=req.page_w_mm,
            page_h_mm=req.page_h_mm,
            margin_top_mm=req.margin_top_mm,
            margin_right_mm=req.margin_right_mm,
            margin_bottom_mm=req.margin_bottom_mm,
            margin_left_mm=req.margin_left_mm,
            spacing_mm=req.spacing_mm,
            columns=req.columns,
            target_row_height_mm=req.target_row_height_mm,
            layout_type=req.layout_type,
        )
        photos = [
            PhotoMeta(id=p["id"], w_px=int(p["w_px"]), h_px=int(p["h_px"])) for p in req.photos
        ]
        locked = {
            k: PhotoOverride(
                page=int(v["page"]),
                x_mm=float(v["x_mm"]),
                y_mm=float(v["y_mm"]),
                w_mm=float(v["w_mm"]),
                h_mm=float(v["h_mm"]),
            )
            for k, v in req.locked_overrides.items()
        }
        size_ov = {
            k: SizeOverride(w_mm=float(v["w_mm"]), h_mm=float(v["h_mm"]))
            for k, v in req.size_overrides.items()
        }
        result = run_layout(
            page_cfg,
            photos,
            locked,
            req.relock_behaviour,
            size_overrides=size_ov,
            cover_photo_id=req.cover_photo_id,
        )
        return {
            "page_count": result.page_count,
            "placements": [
                {
                    "photo_id": p.photo_id,
                    "page": p.page,
                    "x_mm": p.x_mm,
                    "y_mm": p.y_mm,
                    "w_mm": p.w_mm,
                    "h_mm": p.h_mm,
                    "locked": p.locked,
                }
                for p in result.placements
            ],
        }

    # --- Session ---

    @app.get("/api/session/{album_name}")
    async def get_session(album_name: str) -> dict[str, Any]:
        return load_session(album_name)

    @app.post("/api/session/{album_name}")
    async def post_session(album_name: str, data: dict[str, Any]) -> dict[str, Any]:
        save_session(album_name, data)
        return {"ok": True}

    # --- PDF export ---

    @app.post("/api/export/pdf")
    async def export_pdf(req: ExportRequest) -> Response:
        album_path = (_IMAGES_DIR / req.album_name).resolve()
        if not album_path.is_relative_to(_IMAGES_DIR):
            raise HTTPException(status_code=400, detail="Invalid album name")
        placements = [
            PhotoPlacement(
                photo_id=p["photo_id"],
                page=int(p["page"]),
                x_mm=float(p["x_mm"]),
                y_mm=float(p["y_mm"]),
                w_mm=float(p["w_mm"]),
                h_mm=float(p["h_mm"]),
                locked=bool(p.get("locked", False)),
            )
            for p in req.layout_result.get("placements", [])
        ]
        layout = LayoutResult(
            placements=placements,
            page_count=int(req.layout_result.get("page_count", 1)),
        )
        pdf_bytes = generate_pdf(
            layout,
            album_path=album_path,
            page_w_mm=req.page_w_mm,
            page_h_mm=req.page_h_mm,
            jpeg_quality=req.jpeg_quality,
            target_dpi=req.target_dpi,
            cover_title=req.cover_title,
            watermark_text=req.watermark_text or None,
            captions=req.captions or None,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=album.pdf"},
        )

    # --- Static files (must be last) ---

    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
