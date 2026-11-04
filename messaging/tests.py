from django.test import SimpleTestCase

from .whatsapp import build_whatsapp_link


class WhatsappLinkTests(SimpleTestCase):
    def test_strips_plus_and_encodes_message(self):
        link = build_whatsapp_link("+256772123456", "Hello there! 50% off")
        self.assertTrue(link.startswith("https://wa.me/256772123456?text="))
        self.assertIn("Hello%20there%21%2050%25%20off", link)

    def test_strips_non_digit_characters_from_phone(self):
        link = build_whatsapp_link("+256 772-123 456", "hi")
        self.assertTrue(link.startswith("https://wa.me/256772123456?text="))
