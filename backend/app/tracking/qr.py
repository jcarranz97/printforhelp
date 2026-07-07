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

# DejaVu Sans (installed via the Dockerfile) covers Latin accents so Spanish
# label/message text renders correctly; Pillow's built-in default font does
# not. Fall back to the default only if the file is missing (e.g. a bare dev
# box) — captions are ASCII, so the fallback still works there.
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(size: int) -> _Font:
    """Load the accent-capable print font at ``size`` (default-font fallback)."""
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:  # pragma: no cover - only when the font pkg is absent
        return ImageFont.load_default(size=size)


# Call-to-action printed under every QR inviting whoever handles the package
# to scan and log where the aid is. Spanish, per v1 UI. No brand line is
# printed: contributions come from any maker, so the sheet stays unbranded.
_SCAN_CTA_TEXT = (
    "Por favor, escanea este QR y ayúdanos a saber si esta ayuda va en "
    "camino o si ya llegó a quien la necesitaba."
)
_CTA_COLOR = (70, 70, 70)
_CTA_FONT = 11  # PNG contexts (px)
_PDF_CTA_FONT_MM = 2.6  # PDF contexts (mm -> px below)

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

# Part-label grid (used when the maker folds the Resource's print label into
# the bundle). The label is *not* placed beside each QR — that alignment is
# fiddly to print. Instead the bundle prints one page-run of label copies (one
# per unit) followed by the plain QR grid, so a maker prints both stacks and
# pairs them by hand. On-screen (PNG) the two grids stack on one sheet.
_LABEL_COLS = 2
_LABEL_TILE_W = 360  # on-screen label copy width (px)
_LABEL_MAX_H = 240  # on-screen label copy height cap (px)
_PDF_LABEL_COLS = 2
_PDF_LABEL_GAP = round(8 * _MM)
_PDF_LABEL_MAX_H = round(50 * _MM)  # printed label copy height cap


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


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: _Font,
    width: int,
    y: float,
    fill: str | tuple[int, int, int],
) -> None:
    """Draw ``text`` horizontally centered within ``width`` at height ``y``."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) / 2, y), text, fill=fill, font=font)


def _cell(
    url: str,
    caption: str,
    font: _Font,
    qr_size: int,
    caption_h: int,
    *,
    cta_font: _Font | None = None,
    message_lines: list[str] | None = None,
    message_font: _Font | None = None,
    message_line_h: int = 0,
    message_h: int = 0,
) -> Image.Image:
    """Render one QR cell: caption and the scan call-to-action.

    Below the code sit the caption, then the ``_SCAN_CTA_TEXT`` invitation
    (when ``cta_font`` is given). When ``message_lines`` are given, the
    (already word-wrapped) note is drawn *above* the QR, so the message-only
    bundle keeps the compact grid.
    """
    cta_lines, cta_line_h, cta_h = (
        _wrapped_message(_SCAN_CTA_TEXT, cta_font, qr_size) if cta_font else ([], 0, 0)
    )
    cell = Image.new("RGB", (qr_size, message_h + qr_size + caption_h + cta_h), "white")
    draw = ImageDraw.Draw(cell)
    if message_lines and message_font:
        y = 0
        for line in message_lines:
            _draw_centered(draw, line, message_font, qr_size, y, "black")
            y += message_line_h
    top = message_h
    cell.paste(_qr_image(url).resize((qr_size, qr_size)), (0, top))
    _draw_centered(
        draw, caption, font, qr_size, top + qr_size + caption_h * 0.15, "black"
    )
    if cta_font:
        y = top + qr_size + caption_h
        for line in cta_lines:
            _draw_centered(draw, line, cta_font, qr_size, y, _CTA_COLOR)
            y += cta_line_h
    return cell


# --------------------------------------------------------------------------- #
# Shared image helpers (fit / wrap / measure)
# --------------------------------------------------------------------------- #
def _fit_within(image: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scale ``image`` to span ``max_w`` wide, capped at ``max_h`` tall."""
    scale = max_w / image.width
    if image.height * scale > max_h:
        scale = max_h / image.height
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size)


def _wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: _Font, max_width: int
) -> list[str]:
    """Word-wrap ``text`` to lines no wider than ``max_width`` pixels."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _line_height(draw: ImageDraw.ImageDraw, font: _Font) -> int:
    """A single line's height plus a little leading, for any font type."""
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    height = int(bbox[3] - bbox[1])
    return height + max(2, height // 4)


def _wrapped_message(
    message: str, font: _Font, max_width: int
) -> tuple[list[str], int, int]:
    """Wrap ``message`` to ``max_width`` and return (lines, line_h, block_h)."""
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap_text(draw, message, font, max_width)
    line_h = _line_height(draw, font)
    # A half-line of breathing room under the note before the QR starts.
    return lines, line_h, line_h * len(lines) + line_h // 2


# --------------------------------------------------------------------------- #
# Part-label grid (all label copies, printed before the QR pages)
# --------------------------------------------------------------------------- #
def _stack_vertically(images: list[Image.Image], gap: int) -> Image.Image:
    """Stack ``images`` top-to-bottom, centered, on one white canvas."""
    width = max(image.width for image in images)
    height = sum(image.height for image in images) + gap * (len(images) - 1)
    sheet = Image.new("RGB", (width, height), "white")
    y = 0
    for image in images:
        sheet.paste(image, ((width - image.width) // 2, y))
        y += image.height + gap
    return sheet


def build_label_sheet(label_image: Image.Image, count: int) -> Image.Image:
    """Tile ``count`` copies of the part label into an on-screen grid."""
    cols = min(_LABEL_COLS, max(1, count))
    tile = _fit_within(label_image, _LABEL_TILE_W, _LABEL_MAX_H)
    rows = (count + cols - 1) // cols
    width = _PADDING * 2 + cols * tile.width + (cols - 1) * _PADDING
    height = _PADDING * 2 + rows * tile.height + (rows - 1) * _PADDING
    sheet = Image.new("RGB", (width, height), "white")
    for index in range(count):
        col = index % cols
        row = index // cols
        x = _PADDING + col * (tile.width + _PADDING)
        y = _PADDING + row * (tile.height + _PADDING)
        sheet.paste(tile, (x, y))
    return sheet


def build_label_pages(label_image: Image.Image, count: int) -> list[Image.Image]:
    """Paginate ``count`` copies of the part label onto A4 pages.

    Printed *before* the QR pages so a maker runs off one stack of labels and
    one of codes, then pairs them by hand — far easier than aligning a code
    beside each label on a single sticker.
    """
    cols = _PDF_LABEL_COLS
    usable_w = _A4_W - 2 * _PAGE_MARGIN
    cell_w = (usable_w - (cols - 1) * _PDF_LABEL_GAP) // cols
    tile = _fit_within(label_image, cell_w, _PDF_LABEL_MAX_H)
    usable_h = _A4_H - 2 * _PAGE_MARGIN
    rows = max(1, (usable_h + _PDF_LABEL_GAP) // (tile.height + _PDF_LABEL_GAP))
    per_page = cols * rows
    grid_w = cols * cell_w + (cols - 1) * _PDF_LABEL_GAP
    start_x = (_A4_W - grid_w) // 2

    pages: list[Image.Image] = []
    for start in range(0, max(1, count), per_page):
        page = Image.new("RGB", (_A4_W, _A4_H), "white")
        for index in range(start, min(start + per_page, count)):
            slot = index - start
            col = slot % cols
            row = slot // cols
            # Center the (possibly height-capped) tile within its cell width.
            x = start_x + col * (cell_w + _PDF_LABEL_GAP) + (cell_w - tile.width) // 2
            y = _PAGE_MARGIN + row * (tile.height + _PDF_LABEL_GAP)
            page.paste(tile, (x, y))
        pages.append(page)
    return pages


def build_bundle_image(
    labeled_urls: list[tuple[str, str]], message: str | None = None
) -> Image.Image:
    """Compose a single captioned grid image from ``(caption, url)`` pairs.

    The first pair is expected to be the group code; the rest are item codes.
    Cells flow left-to-right, top-to-bottom in a fixed-column grid. When a
    ``message`` is given it is drawn above every QR (still a compact grid).
    Used for the on-screen PNG download.
    """
    font = _font(14)
    cta_font = _font(_CTA_FONT)
    message_font = _font(14)
    msg_lines, msg_line_h, msg_h = (
        _wrapped_message(message, message_font, _QR_SIZE) if message else ([], 0, 0)
    )
    cells = [
        _cell(
            url,
            caption,
            font,
            _QR_SIZE,
            _CAPTION_H,
            cta_font=cta_font,
            message_lines=msg_lines,
            message_font=message_font,
            message_line_h=msg_line_h,
            message_h=msg_h,
        )
        for caption, url in labeled_urls
    ]

    cols = min(_COLS, max(1, len(cells)))
    rows = (len(cells) + cols - 1) // cols
    cell_w = _QR_SIZE
    # The scan CTA/message grow the cell; take the actual height from a cell.
    cell_h = cells[0].height
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


def bundle_png_bytes(
    labeled_urls: list[tuple[str, str]],
    label_image: Image.Image | None = None,
    message: str | None = None,
) -> bytes:
    """Render the QR bundle as a single-sheet PNG.

    A ``label_image`` stacks a grid of part-label copies (one per unit) above
    the QR grid, so the maker cuts them out and pairs them by hand. A
    ``message`` (with or without a label) prints the note above each QR. With
    neither it is the plain QR grid.
    """
    if label_image is not None:
        sheet = _stack_vertically(
            [
                build_label_sheet(label_image, len(labeled_urls)),
                build_bundle_image(labeled_urls, message),
            ],
            _PADDING,
        )
    else:
        sheet = build_bundle_image(labeled_urls, message)
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    return buffer.getvalue()


def _cells_per_page(cell_h: int) -> int:
    """Number of QR cells that fit on one A4 page for a given cell height."""
    usable_h = _A4_H - 2 * _PAGE_MARGIN
    rows = max(1, (usable_h + _PDF_GAP) // (cell_h + _PDF_GAP))
    return _PDF_COLS * rows


def _render_page(page_cells: list[Image.Image], cell_h: int) -> Image.Image:
    """Lay up to a full page of cells onto one white A4 canvas, top-centered."""
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


def build_pdf_pages(
    labeled_urls: list[tuple[str, str]], message: str | None = None
) -> list[Image.Image]:
    """Render the bundle as A4 pages of captioned QR cells (3 per row).

    A ``message`` is drawn above every QR, which grows each cell and so fits
    fewer rows per page while keeping the three-per-row grid.
    """
    font = _font(round(3.5 * _MM))
    cta_font = _font(round(_PDF_CTA_FONT_MM * _MM))
    message_font = _font(round(3 * _MM))
    msg_lines, msg_line_h, msg_h = (
        _wrapped_message(message, message_font, _PDF_QR) if message else ([], 0, 0)
    )
    cells = [
        _cell(
            url,
            caption,
            font,
            _PDF_QR,
            _PDF_CAPTION_H,
            cta_font=cta_font,
            message_lines=msg_lines,
            message_font=message_font,
            message_line_h=msg_line_h,
            message_h=msg_h,
        )
        for caption, url in labeled_urls
    ]
    # The scan CTA/message grow the cell; take the actual height from a cell.
    cell_h = cells[0].height
    per_page = _cells_per_page(cell_h)
    return [
        _render_page(cells[start : start + per_page], cell_h)
        for start in range(0, len(cells), per_page)
    ]


def bundle_pdf_bytes(
    labeled_urls: list[tuple[str, str]],
    label_image: Image.Image | None = None,
    message: str | None = None,
) -> bytes:
    """Render the QR bundle as a print-ready, multi-page A4 PDF.

    A ``label_image`` prints a page-run of part-label copies (one per unit)
    *first*, then the QR grid pages, so the maker prints both stacks and pairs
    them by hand. A ``message`` (with or without a label) is drawn above each
    QR. With neither it is the plain three-per-row grid.
    """
    if label_image is not None:
        pages = build_label_pages(label_image, len(labeled_urls))
        pages += build_pdf_pages(labeled_urls, message)
    else:
        pages = build_pdf_pages(labeled_urls, message)
    buffer = io.BytesIO()
    pages[0].save(
        buffer,
        format="PDF",
        resolution=float(_DPI),
        save_all=True,
        append_images=pages[1:],
    )
    return buffer.getvalue()
