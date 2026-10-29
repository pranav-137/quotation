"""PDF generation for quotations (ReportLab, pure Python)."""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ACCENT = colors.HexColor("#1f4e79")
LIGHT = colors.HexColor("#eef3f8")


def money(value):
    """Format a Decimal in Indian digit grouping, e.g. 1,23,456.00"""
    value = Decimal(value).quantize(Decimal("0.01"))
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return f"{sign}{whole}.{frac}"


def multiline(text):
    return escape(text or "").replace("\r\n", "\n").replace("\n", "<br/>")


def build_pdf(quote):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Quotation {quote.estimate_number}", author=quote.company_name,
    )
    base = getSampleStyleSheet()["Normal"]
    normal = ParagraphStyle("n", parent=base, fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=normal, fontSize=8.5, leading=11.5)
    bold = ParagraphStyle("b", parent=normal, fontName="Helvetica-Bold")
    title = ParagraphStyle("t", parent=normal, fontName="Helvetica-Bold", fontSize=20, leading=24,
                           textColor=ACCENT, alignment=2)
    company = ParagraphStyle("c", parent=normal, fontName="Helvetica-Bold", fontSize=13, leading=16)
    right = ParagraphStyle("r", parent=normal, alignment=2)
    head = ParagraphStyle("h", parent=normal, fontName="Helvetica-Bold", textColor=colors.white)
    head_r = ParagraphStyle("hr", parent=head, alignment=2)
    section = ParagraphStyle("sec", parent=normal, fontName="Helvetica-Bold", textColor=ACCENT, spaceBefore=8, spaceAfter=3)

    story = []

    # ---- Header: logo + company | title ----
    left_cells = []
    if quote.logo_bytes:
        try:
            w, h = ImageReader(BytesIO(quote.logo_bytes)).getSize()
            max_w, max_h = 45 * mm, 22 * mm
            ratio = min(max_w / w, max_h / h)
            left_cells.append(Image(BytesIO(quote.logo_bytes), width=w * ratio, height=h * ratio, hAlign="LEFT"))
            left_cells.append(Spacer(1, 3))
        except Exception:
            pass  # a bad/missing logo should never block the download
    left_cells.append(Paragraph(escape(quote.company_name), company))
    left_cells.append(Paragraph(multiline(quote.company_address), normal))
    if quote.company_gstin:
        left_cells.append(Paragraph(f"<b>GSTIN:</b> {escape(quote.company_gstin)}", normal))

    meta = [
        [Paragraph("Estimate No:", normal), Paragraph(f"<b>{escape(quote.estimate_number)}</b>", right)],
        [Paragraph("Date:", normal), Paragraph(quote.date.strftime("%d %b %Y"), right)],
        [Paragraph("Valid till:", normal), Paragraph(quote.valid_till.strftime("%d %b %Y"), right)],
    ]
    meta_tbl = Table(meta, colWidths=[28 * mm, 40 * mm])
    meta_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                                  ("TOPPADDING", (0, 0), (-1, -1), 1)]))
    right_cells = [Paragraph("QUOTATION", title), Spacer(1, 6), meta_tbl]
    header = Table([[left_cells, right_cells]], colWidths=[105 * mm, 75 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [header, Spacer(1, 8)]

    # ---- Customer ----
    cust = [Paragraph("QUOTATION FOR", section), Paragraph(f"<b>{escape(quote.customer_name)}</b>", normal)]
    if quote.customer_address:
        cust.append(Paragraph(multiline(quote.customer_address), normal))
    if quote.customer_gstin:
        cust.append(Paragraph(f"<b>GSTIN:</b> {escape(quote.customer_gstin)}", normal))
    story += cust + [Spacer(1, 8)]

    # ---- Items ----
    rows = [[
        Paragraph("#", head), Paragraph("Description", head), Paragraph("HSN/SAC", head),
        Paragraph("Qty", head_r), Paragraph("Rate", head_r), Paragraph("Amount", head_r),
        Paragraph("GST", head_r), Paragraph("Total", head_r),
    ]]
    for n, item in enumerate(quote.items, start=1):
        gst_label = f"{item.gst_percent}%<br/>{money(item.gst_amount)}" if item.gst_applicable else "-"
        rows.append([
            Paragraph(str(n), normal),
            Paragraph(escape(item.description), normal),
            Paragraph(escape(item.hsn_code or "-"), normal),
            Paragraph(f"{item.quantity.normalize():f}", right),
            Paragraph(money(item.rate), right),
            Paragraph(money(item.amount), right),
            Paragraph(gst_label, ParagraphStyle("g", parent=right, fontSize=8)),
            Paragraph(money(item.total), right),
        ])
    items_tbl = Table(rows, repeatRows=1,
                      colWidths=[8 * mm, 56 * mm, 20 * mm, 14 * mm, 22 * mm, 22 * mm, 20 * mm, 22 * mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d3dd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [items_tbl, Spacer(1, 8)]

    # ---- Totals ----
    totals = [
        [Paragraph("Subtotal", normal), Paragraph("Rs. " + money(quote.subtotal), right)],
        [Paragraph("Total GST", normal), Paragraph("Rs. " + money(quote.total_gst), right)],
        [Paragraph("Grand Total", bold), Paragraph("Rs. " + money(quote.grand_total), ParagraphStyle("gt", parent=right, fontName="Helvetica-Bold", fontSize=11))],
    ]
    totals_tbl = Table(totals, colWidths=[35 * mm, 40 * mm], hAlign="RIGHT")
    totals_tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 2), (-1, 2), 0.8, ACCENT),
        ("BACKGROUND", (0, 2), (-1, 2), LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [totals_tbl]

    # ---- Notes / Terms ----
    if quote.notes:
        story += [Paragraph("NOTES", section), Paragraph(multiline(quote.notes), small)]
    if quote.terms:
        story += [Paragraph("TERMS &amp; CONDITIONS", section), Paragraph(multiline(quote.terms), small)]

    story += [Spacer(1, 14), Paragraph("This is a computer-generated quotation.",
                                       ParagraphStyle("f", parent=small, textColor=colors.grey, alignment=1))]

    doc.build(story)
    return buf.getvalue()
