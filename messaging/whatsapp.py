from urllib.parse import quote


def build_whatsapp_link(phone, message):
    """Build a wa.me click-to-chat link. `phone` may be E.164 (+2567...) or similar."""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return f"https://wa.me/{digits}?text={quote(message, safe='')}"
