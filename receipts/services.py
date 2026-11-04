from io import BytesIO

from django.db import transaction
from django.utils import timezone
from num2words import num2words

from core.models import LandlordProfile
from core.templatetags.currency import ugx
from tenants.services import format_month_range, get_pending_months, get_tenancy_balance
from .models import Receipt, ReceiptSequence


def amount_in_words(amount):
    """e.g. 450000 -> 'Four hundred fifty thousand shillings only'."""
    words = num2words(int(amount), lang="en")
    words = words.replace(" and ", " ")
    return f"{words[0].upper()}{words[1:]} shillings only"


def allocate_receipt_number(year=None):
    year = year or timezone.now().year
    with transaction.atomic():
        ReceiptSequence.objects.get_or_create(year=year)
        seq = ReceiptSequence.objects.select_for_update().get(year=year)
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
        return f"RCP-{year}-{seq.last_number:05d}"


def get_or_create_receipt(payment):
    try:
        return payment.receipt
    except Receipt.DoesNotExist:
        pass
    number = allocate_receipt_number(year=payment.payment_date.year)
    return Receipt.objects.create(payment=payment, receipt_number=number)


def _receipt_context(payment):
    receipt = get_or_create_receipt(payment)
    tenancy = payment.tenancy
    balance = get_tenancy_balance(tenancy, as_of=payment.payment_date)
    pending_months = get_pending_months(tenancy, as_of=payment.payment_date)
    landlord = LandlordProfile.get_solo()

    recorded_by = payment.recorded_by
    signer_profile = getattr(recorded_by, "profile", None) if recorded_by else None
    signer_name = recorded_by.get_full_name() or recorded_by.username if recorded_by else None
    signature_path = None
    if (
        signer_profile
        and signer_profile.signature
        and signer_profile.signature.storage.exists(signer_profile.signature.name)
    ):
        signature_path = signer_profile.signature.path

    return {
        "landlord": landlord,
        "payment": payment,
        "receipt": receipt,
        "tenancy": tenancy,
        "tenant": tenancy.tenant,
        "unit": tenancy.unit,
        "property": tenancy.unit.property,
        "amount_words": amount_in_words(payment.amount),
        "balance": balance,
        "pending_months_display": format_month_range(pending_months),
        "signer_name": signer_name,
        "signature_path": signature_path,
        "header_business_name": (
            signer_profile.business_name
            if signer_profile and signer_profile.business_name
            else landlord.business_name
        ),
        "header_phone": signer_profile.phone if signer_profile and signer_profile.phone else landlord.phone,
        "header_address": tenancy.unit.property.location,
    }


def render_receipt_pdf(payment):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Flowable,
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    ctx = _receipt_context(payment)
    landlord = ctx["landlord"]
    receipt = ctx["receipt"]
    balance = ctx["balance"]

    class HRule(Flowable):
        def __init__(self, width, thickness=1.2, color=colors.HexColor("#222222")):
            super().__init__()
            self.width = width
            self.thickness = thickness
            self.color = color

        def draw(self):
            self.canv.setStrokeColor(self.color)
            self.canv.setLineWidth(self.thickness)
            self.canv.line(0, 0, self.width, 0)

    business_style = ParagraphStyle("business", fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1)
    muted_style = ParagraphStyle("muted", fontName="Helvetica", fontSize=9, leading=12, alignment=1, textColor=colors.HexColor("#555555"))
    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, spaceBefore=10, spaceAfter=10
    )
    label_style = ParagraphStyle("label", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#555555"))
    value_style = ParagraphStyle("value", fontName="Helvetica", fontSize=10, leading=13)
    amount_figures_style = ParagraphStyle("amount_figures", fontName="Helvetica-Bold", fontSize=14, leading=17)
    amount_words_style = ParagraphStyle("amount_words", fontName="Helvetica-Oblique", fontSize=10, leading=13)
    balance_arrears_style = ParagraphStyle("balance_arrears", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#bb0000"))
    balance_credit_style = ParagraphStyle("balance_credit", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#007766"))
    footer_style = ParagraphStyle("footer", fontName="Helvetica", fontSize=8, leading=11, alignment=1, textColor=colors.HexColor("#555555"))

    buffer = BytesIO()
    page_width, page_height = A5
    margin = 14 * mm
    content_width = page_width - 2 * margin
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    story = []

    header_left = [Paragraph(ctx["header_business_name"] or "", business_style)]
    if ctx["header_address"]:
        header_left.append(Paragraph(ctx["header_address"], muted_style))
    if ctx["header_phone"]:
        header_left.append(Paragraph(str(ctx["header_phone"]), muted_style))

    if landlord.logo and landlord.logo.storage.exists(landlord.logo.name):
        logo_width, logo_height = ImageReader(landlord.logo.path).getSize()
        max_h = 18 * mm
        logo_flowable = Image(landlord.logo.path, width=max_h * logo_width / logo_height, height=max_h)
        header_table = Table(
            [[header_left, logo_flowable]],
            colWidths=[content_width - logo_flowable.drawWidth - 4, logo_flowable.drawWidth],
        )
    else:
        header_table = Table([[header_left]], colWidths=[content_width])

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRule(content_width, thickness=1.5))
    story.append(Spacer(1, 2))

    story.append(Paragraph("PAYMENT RECEIPT", title_style))

    details_rows = [
        ("Receipt No.", receipt.receipt_number),
        ("Date", payment.payment_date.strftime("%d %b %Y")),
        ("Received from", ctx["tenant"].full_name),
        ("Property / Unit", f"{ctx['property'].name} – {ctx['unit'].name}"),
        ("Period covered", payment.period_display()),
        (
            "Payment method",
            payment.get_method_display() + (f" ({payment.reference})" if payment.reference else ""),
        ),
    ]
    if payment.notes:
        details_rows.append(("Notes", payment.notes))
    details_table = Table(
        [[Paragraph(label, label_style), Paragraph(str(value), value_style)] for label, value in details_rows],
        colWidths=[content_width * 0.38, content_width * 0.62],
    )
    details_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 12))

    amount_box = Table(
        [
            [Paragraph(ugx(payment.amount), amount_figures_style)],
            [Paragraph(ctx["amount_words"], amount_words_style)],
        ],
        colWidths=[content_width],
    )
    amount_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#222222")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(amount_box)
    story.append(Spacer(1, 10))

    if balance.is_in_arrears:
        pending_suffix = f" ({ctx['pending_months_display']})" if ctx["pending_months_display"] else ""
        story.append(
            Paragraph(f"Outstanding balance: {ugx(balance.balance)}{pending_suffix}", balance_arrears_style)
        )
    elif balance.is_in_credit:
        story.append(Paragraph(f"Credit balance: {ugx(balance.abs_balance)}", balance_credit_style))

    signer_name = ctx["signer_name"]
    signature_path = ctx["signature_path"]

    if signature_path:
        sig_width, sig_height = ImageReader(signature_path).getSize()
        max_sig_h = 14 * mm
        story.append(Spacer(1, 20))
        story.append(Image(signature_path, width=max_sig_h * sig_width / sig_height, height=max_sig_h))
        story.append(Spacer(1, 2))
    else:
        story.append(Spacer(1, 28))

    signature_line = Table([[""]], colWidths=[content_width * 0.6], rowHeights=[0.1])
    signature_line.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor("#222222"))]))
    story.append(signature_line)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Received by: {signer_name}" if signer_name else "Received by", label_style))

    if landlord.receipt_footer_text:
        story.append(Spacer(1, 16))
        story.append(Paragraph(landlord.receipt_footer_text, footer_style))

    doc.build(story)
    return buffer.getvalue()


def render_receipt_jpg(payment):
    import fitz

    pdf_bytes = render_receipt_pdf(payment)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    return pixmap.tobytes("jpg")
