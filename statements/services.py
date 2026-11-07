import hashlib
import secrets
from io import BytesIO


def generate_raw_token():
    return secrets.token_urlsafe(32)


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()


def render_statement_pdf(tenant, tenancies):
    """A printable PDF of a tenant's statement: one section per tenancy with its payment history."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from django.utils import timezone

    from core.models import LandlordProfile
    from core.templatetags.currency import ugx

    landlord = LandlordProfile.get_solo()

    business_style = ParagraphStyle("business", fontName="Helvetica-Bold", fontSize=14, leading=17)
    muted_style = ParagraphStyle(
        "muted", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#555555")
    )
    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=10, spaceAfter=4
    )
    section_style = ParagraphStyle(
        "section", fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=12, spaceAfter=4
    )
    label_style = ParagraphStyle("label", fontName="Helvetica", fontSize=9, leading=12)
    balance_arrears_style = ParagraphStyle(
        "balance_arrears",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#bb0000"),
        spaceAfter=6,
    )
    balance_credit_style = ParagraphStyle(
        "balance_credit",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#007766"),
        spaceAfter=6,
    )
    balance_settled_style = ParagraphStyle(
        "balance_settled",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )
    header_cell_style = ParagraphStyle(
        "header_cell", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white
    )
    cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=11)
    footer_style = ParagraphStyle(
        "footer", fontName="Helvetica", fontSize=8, leading=11, alignment=1, textColor=colors.HexColor("#555555")
    )

    buffer = BytesIO()
    page_width, page_height = A4
    margin = 16 * mm
    content_width = page_width - 2 * margin
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    story = [Paragraph(landlord.business_name or "", business_style)]
    if landlord.address:
        story.append(Paragraph(landlord.address, muted_style))
    if landlord.phone:
        story.append(Paragraph(str(landlord.phone), muted_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("TENANT STATEMENT", title_style))
    story.append(Paragraph(f"Tenant: {tenant.full_name}", label_style))
    story.append(Paragraph(f"Generated: {timezone.now().strftime('%d %b %Y, %I:%M %p')}", muted_style))

    col_widths = [
        content_width * 0.11,
        content_width * 0.13,
        content_width * 0.12,
        content_width * 0.15,
        content_width * 0.13,
        content_width * 0.22,
        content_width * 0.14,
    ]

    for item in tenancies:
        tenancy = item["tenancy"]
        story.append(Spacer(1, 4))
        unit_label = f"{tenancy.unit} ({tenancy.start_date.strftime('%d %b %Y')}"
        unit_label += (
            f" – {tenancy.end_date.strftime('%d %b %Y')})" if tenancy.end_date else " – present)"
        )
        story.append(Paragraph(unit_label, section_style))
        story.append(Paragraph(f"Monthly rent: {ugx(tenancy.agreed_monthly_rent)}", label_style))

        balance = item["balance"]
        if balance.is_in_arrears:
            suffix = f" ({item['pending_months_display']})" if item["pending_months_display"] else ""
            story.append(
                Paragraph(f"Outstanding balance: {ugx(balance.balance)}{suffix}", balance_arrears_style)
            )
        elif balance.is_in_credit:
            story.append(Paragraph(f"Credit balance: {ugx(balance.abs_balance)}", balance_credit_style))
        else:
            story.append(Paragraph("Settled", balance_settled_style))

        header_row = [
            Paragraph(h, header_cell_style)
            for h in ["Date", "Period", "Amount", "Method", "Reference", "Notes", "Receipt"]
        ]
        rows = [header_row]
        payments = list(item["payments"])
        if payments:
            for payment in payments:
                rows.append(
                    [
                        Paragraph(payment.payment_date.strftime("%d %b %Y"), cell_style),
                        Paragraph(payment.period_display(), cell_style),
                        Paragraph(ugx(payment.amount), cell_style),
                        Paragraph(payment.get_method_display(), cell_style),
                        Paragraph(payment.reference or "—", cell_style),
                        Paragraph(payment.notes or "", cell_style),
                        Paragraph(
                            payment.receipt.receipt_number if getattr(payment, "receipt", None) else "—",
                            cell_style,
                        ),
                    ]
                )
        else:
            rows.append([Paragraph("No payments recorded yet.", cell_style), "", "", "", "", "", ""])

        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

    if landlord.receipt_footer_text:
        story.append(Spacer(1, 16))
        story.append(Paragraph(landlord.receipt_footer_text, footer_style))

    doc.build(story)
    return buffer.getvalue()
