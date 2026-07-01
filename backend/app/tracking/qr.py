"""QR-code rendering for tracking tokens.

The QR only ever encodes a public tracking URL (``{base}/track/{token}``) —
nothing else — so the phone's native camera is enough to open it. Single
codes render as PNG; the printable *bundle* lays the group code and every
item code out as captioned cells. The **PDF** paginates those cells onto
standard **A4 pages** at a fixed physical size, so a maker can print it
straight away (multiple pages when there are many items). The PNG keeps the
single-sheet grid for on-screen use.
"""

from __future__ import annotations

import io

import qrcode
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from qrcode.image.pil import PilImage

# ``load_default`` returns either of these Pillow font types.
_Font = ImageFont.ImageFont | FreeTypeFont

# On-screen PNG grid layout (pixels).
_QR_SIZE = 240
_CAPTION_H = 28
_PADDING = 24
_COLS = 3

# A4 print layout, in pixels at 150 DPI (A4 = 210 x 297 mm).
_DPI = 150
_MM = _DPI / 25.4  # pixels per millimetre
_A4_W = round(210 * _MM)
_A4_H = round(297 * _MM)
_PAGE_MARGIN = round(15 * _MM)
_PDF_QR = round(45 * _MM)  # printed QR square edge (~45 mm)
_PDF_CAPTION_H = round(7 * _MM)
_PDF_GAP = round(9 * _MM)  # gap between cells
_PDF_COLS = 3


def track_url(base_url: str, token: str) -> str:
    """Return the public tracking URL a QR should encode."""
    return f"{base_url.rstrip('/')}/track/{token}"


def _qr_image(url: str, box_size: int = 10) -> Image.Image:
    """Render one QR code for ``url`` as an RGB Pillow image."""
    qr = qrcode.QRCode(box_size=box_size, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(
        fill_color="black", back_color="white", image_factory=PilImage
    )
    return image.get_image().convert("RGB")


def qr_png_bytes(url: str) -> bytes:
    """Render one QR code for ``url`` as PNG bytes."""
    buffer = io.BytesIO()
    _qr_image(url).save(buffer, format="PNG")
    return buffer.getvalue()


def _cell(
    url: str, caption: str, font: _Font, qr_size: int, caption_h: int
) -> Image.Image:
    """Render one captioned QR cell (code above a centered label)."""
    cell = Image.new("RGB", (qr_size, qr_size + caption_h), "white")
    code = _qr_image(url).resize((qr_size, qr_size))
    cell.paste(code, (0, 0))
    draw = ImageDraw.Draw(cell)
    bbox = draw.textbbox((0, 0), caption, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((qr_size - text_w) / 2, qr_size + caption_h * 0.15),
        caption,
        fill="black",
        font=font,
    )
    return cell


def build_bundle_image(labeled_urls: list[tuple[str, str]]) -> Image.Image:
    """Compose a single captioned grid image from ``(caption, url)`` pairs.

    The first pair is expected to be the group code; the rest are item codes.
    Cells flow left-to-right, top-to-bottom in a fixed-column grid. Used for
    the on-screen PNG download.
    """
    font = ImageFont.load_default()
    cells = [
        _cell(url, caption, font, _QR_SIZE, _CAPTION_H) for caption, url in labeled_urls
    ]

    cols = min(_COLS, max(1, len(cells)))
    rows = (len(cells) + cols - 1) // cols
    cell_w = _QR_SIZE
    cell_h = _QR_SIZE + _CAPTION_H
    width = _PADDING * 2 + cols * cell_w + (cols - 1) * _PADDING
    height = _PADDING * 2 + rows * cell_h + (rows - 1) * _PADDING

    sheet = Image.new("RGB", (width, height), "white")
    for index, cell in enumerate(cells):
        col = index % cols
        row = index // cols
        x = _PADDING + col * (cell_w + _PADDING)
        y = _PADDING + row * (cell_h + _PADDING)
        sheet.paste(cell, (x, y))
    return sheet


def bundle_png_bytes(labeled_urls: list[tuple[str, str]]) -> bytes:
    """Render the QR bundle as a single-sheet PNG."""
    buffer = io.BytesIO()
    build_bundle_image(labeled_urls).save(buffer, format="PNG")
    return buffer.getvalue()


def _cells_per_page() -> int:
    """Number of QR cells that fit on one A4 page in the print grid."""
    cell_h = _PDF_QR + _PDF_CAPTION_H
    usable_h = _A4_H - 2 * _PAGE_MARGIN
    rows = max(1, (usable_h + _PDF_GAP) // (cell_h + _PDF_GAP))
    return _PDF_COLS * rows


def _render_page(page_cells: list[Image.Image]) -> Image.Image:
    """Lay up to a full page of cells onto one white A4 canvas, top-centered."""
    cell_h = _PDF_QR + _PDF_CAPTION_H
    grid_w = _PDF_COLS * _PDF_QR + (_PDF_COLS - 1) * _PDF_GAP
    start_x = (_A4_W - grid_w) // 2

    page = Image.new("RGB", (_A4_W, _A4_H), "white")
    for index, cell in enumerate(page_cells):
        col = index % _PDF_COLS
        row = index // _PDF_COLS
        x = start_x + col * (_PDF_QR + _PDF_GAP)
        y = _PAGE_MARGIN + row * (cell_h + _PDF_GAP)
        page.paste(cell, (x, y))
    return page


def build_pdf_pages(labeled_urls: list[tuple[str, str]]) -> list[Image.Image]:
    """Render the bundle as one or more A4 pages of captioned QR cells."""
    font = ImageFont.load_default(size=round(3.5 * _MM))
    cells = [
        _cell(url, caption, font, _PDF_QR, _PDF_CAPTION_H)
        for caption, url in labeled_urls
    ]
    per_page = _cells_per_page()
    return [
        _render_page(cells[start : start + per_page])
        for start in range(0, len(cells), per_page)
    ]


def bundle_pdf_bytes(labeled_urls: list[tuple[str, str]]) -> bytes:
    """Render the QR bundle as a print-ready, multi-page A4 PDF."""
    pages = build_pdf_pages(labeled_urls)
    buffer = io.BytesIO()
    pages[0].save(
        buffer,
        format="PDF",
        resolution=float(_DPI),
        save_all=True,
        append_images=pages[1:],
    )
    return buffer.getvalue()
