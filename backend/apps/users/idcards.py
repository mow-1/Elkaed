import io

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

CARD_W = 85 * mm
CARD_H = 54 * mm


def qr_png_bytes(token: str) -> bytes:
    img = qrcode.make(token)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def draw_card(c, x, y, student):
    """Draw one ID card (student name/year/group + QR) at (x, y) — bottom-left corner,
    card is CARD_W x CARD_H. One function reused by the single-card and bulk 8-up views
    so the layout is written once."""
    c.setLineWidth(0.75)
    c.rect(x, y, CARD_W, CARD_H)

    c.setFont('Helvetica-Bold', 11)
    c.drawString(x + 5 * mm, y + CARD_H - 10 * mm, student.full_name)

    c.setFont('Helvetica', 8)
    year_label = student.get_academic_year_display() if student.academic_year else '—'
    c.drawString(x + 5 * mm, y + CARD_H - 16 * mm, year_label)
    if student.group:
        c.drawString(x + 5 * mm, y + CARD_H - 21 * mm, student.group.name_ar)
    c.drawString(x + 5 * mm, y + 5 * mm, student.phone)

    qr_reader = ImageReader(io.BytesIO(qr_png_bytes(student.attendance_token)))
    qr_size = 28 * mm
    c.drawImage(
        qr_reader,
        x + CARD_W - qr_size - 5 * mm, y + (CARD_H - qr_size) / 2,
        width=qr_size, height=qr_size,
    )


def render_single_card_pdf(student) -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CARD_W + 10 * mm, CARD_H + 10 * mm))
    draw_card(c, 5 * mm, 5 * mm, student)
    c.showPage()
    c.save()
    return buf.getvalue()


def render_bulk_cards_pdf(students) -> bytes:
    """8-up layout on A4 — 2 columns x 4 rows per page."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    cols, rows = 2, 4
    margin_x = (page_w - cols * CARD_W) / (cols + 1)
    margin_y = (page_h - rows * CARD_H) / (rows + 1)

    for i, student in enumerate(students):
        pos = i % (cols * rows)
        if i > 0 and pos == 0:
            c.showPage()
        col = pos % cols
        row = pos // cols
        x = margin_x + col * (CARD_W + margin_x)
        y = page_h - margin_y - (row + 1) * CARD_H - row * margin_y
        draw_card(c, x, y, student)

    c.showPage()
    c.save()
    return buf.getvalue()
