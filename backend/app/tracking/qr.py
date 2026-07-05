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

# Label-sticker layout (used when a part label and/or a contributor message is
# folded into the bundle). Each sticker is one full-width block: the label on
# top, then the message (left) beside the QR (right) — one per printed unit so
# it can be cut out and attached to that package.
# PNG (on-screen) sticker.
_STK_W = 640
_STK_GAP = 18
_STK_LABEL_MAX_H = 170
_STK_MSG_FONT = 15
# PDF (print) sticker — full usable A4 width.
_PDF_STK_W = _A4_W - 2 * _PAGE_MARGIN
_PDF_STK_GAP = round(6 * _MM)
_PDF_STK_LABEL_MAX_H = round(38 * _MM)
_PDF_STK_MSG_FONT = round(3.5 * _MM)


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
# Label-sticker layout (label on top, message + QR below)
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


def _sticker(
    caption: str,
    url: str,
    *,
    width: int,
    qr_size: int,
    caption_font: _Font,
    caption_h: int,
    cta_font: _Font,
    message_font: _Font,
    gap: int,
    scaled_label: Image.Image | None,
    message: str | None,
) -> Image.Image:
    """Compose one printable sticker: label on top, message beside the QR.

    ``scaled_label`` (already sized to ``width``) and ``message`` are optional;
    the QR block (code + caption + scan CTA) is always on the right.
    """
    qr_block = _cell(
        url,
        caption,
        caption_font,
        qr_size,
        caption_h,
        cta_font=cta_font,
    )
    row_h = qr_block.height
    label_h = scaled_label.height + gap if scaled_label is not None else 0
    sticker = Image.new("RGB", (width, label_h + row_h), "white")

    if scaled_label is not None:
        sticker.paste(scaled_label, ((width - scaled_label.width) // 2, 0))

    row_top = label_h
    sticker.paste(qr_block, (width - qr_size, row_top))

    if message:
        draw = ImageDraw.Draw(sticker)
        msg_max_w = width - qr_size - gap
        lines = _wrap_text(draw, message, message_font, msg_max_w)
        # Measure one line's height via the draw (works for any font type) and
        # add a little leading so wrapped lines don't crowd.
        sample = draw.textbbox((0, 0), "Ag", font=message_font)
        line_h = (sample[3] - sample[1]) + max(2, (sample[3] - sample[1]) // 4)
        block_h = line_h * len(lines)
        y = row_top + max(0, (row_h - block_h) // 2)
        for line in lines:
            draw.text((0, y), line, fill="black", font=message_font)
            y += line_h
    return sticker


def _build_stickers(
    labeled_urls: list[tuple[str, str]],
    *,
    width: int,
    qr_size: int,
    caption_font: _Font,
    caption_h: int,
    cta_font: _Font,
    message_font: _Font,
    gap: int,
    label_max_h: int,
    label_image: Image.Image | None,
    message: str | None,
) -> list[Image.Image]:
    """Render one sticker per ``(caption, url)`` pair, sharing label + message."""
    scaled_label = (
        _fit_within(label_image, width, label_max_h)
        if label_image is not None
        else None
    )
    return [
        _sticker(
            caption,
            url,
            width=width,
            qr_size=qr_size,
            caption_font=caption_font,
            caption_h=caption_h,
            cta_font=cta_font,
            message_font=message_font,
            gap=gap,
            scaled_label=scaled_label,
            message=message,
        )
        for caption, url in labeled_urls
    ]


def build_sticker_sheet(
    labeled_urls: list[tuple[str, str]],
    label_image: Image.Image | None,
    message: str | None,
) -> Image.Image:
    """Stack per-unit label stickers vertically for the on-screen PNG."""
    stickers = _build_stickers(
        labeled_urls,
        width=_STK_W,
        qr_size=_QR_SIZE,
        caption_font=_font(16),
        caption_h=_CAPTION_H,
        cta_font=_font(_CTA_FONT),
        message_font=_font(_STK_MSG_FONT),
        gap=_STK_GAP,
        label_max_h=_STK_LABEL_MAX_H,
        label_image=label_image,
        message=message,
    )
    width = _STK_W + 2 * _PADDING
    height = 2 * _PADDING + sum(s.height for s in stickers)
    height += _STK_GAP * max(0, len(stickers) - 1)
    sheet = Image.new("RGB", (width, height), "white")
    y = _PADDING
    for sticker in stickers:
        sheet.paste(sticker, (_PADDING, y))
        y += sticker.height + _STK_GAP
    return sheet


def build_sticker_pages(
    labeled_urls: list[tuple[str, str]],
    label_image: Image.Image | None,
    message: str | None,
) -> list[Image.Image]:
    """Paginate per-unit label stickers onto one or more A4 pages."""
    stickers = _build_stickers(
        labeled_urls,
        width=_PDF_STK_W,
        qr_size=_PDF_QR,
        caption_font=_font(round(3.5 * _MM)),
        caption_h=_PDF_CAPTION_H,
        cta_font=_font(round(_PDF_CTA_FONT_MM * _MM)),
        message_font=_font(_PDF_STK_MSG_FONT),
        gap=_PDF_STK_GAP,
        label_max_h=_PDF_STK_LABEL_MAX_H,
        label_image=label_image,
        message=message,
    )
    usable_h = _A4_H - 2 * _PAGE_MARGIN
    start_x = (_A4_W - _PDF_STK_W) // 2

    pages: list[Image.Image] = []
    page = Image.new("RGB", (_A4_W, _A4_H), "white")
    y = _PAGE_MARGIN
    for sticker in stickers:
        # Start a fresh page when this sticker would overflow (but never leave
        # a page empty, so a single oversized sticker still prints).
        if y > _PAGE_MARGIN and y + sticker.height > _PAGE_MARGIN + usable_h:
            pages.append(page)
            page = Image.new("RGB", (_A4_W, _A4_H), "white")
            y = _PAGE_MARGIN
        page.paste(sticker, (start_x, y))
        y += sticker.height + _PDF_STK_GAP
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

    A ``label_image`` switches to the per-unit label-sticker layout (label on
    top, message beside the QR). A ``message`` without a label keeps the
    compact grid but prints the note above each QR. With neither it is the
    plain QR grid.
    """
    if label_image is not None:
        sheet = build_sticker_sheet(labeled_urls, label_image, message)
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

    A ``label_image`` prints the per-unit label-sticker layout (label on top,
    message beside the QR). A ``message`` without a label keeps the three-per-
    row grid with the note above each QR. With neither it is the plain grid.
    """
    if label_image is not None:
        pages = build_sticker_pages(labeled_urls, label_image, message)
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
