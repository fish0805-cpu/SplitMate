from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class BrandingTests(TestCase):
    def test_home_exposes_favicon_from_staticfiles(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertContains(
            response,
            'rel="icon" type="image/png" href="/static/expenses/images/favicon.png"',
        )
        self.assertIsNotNone(finders.find("expenses/images/favicon.png"))

    def test_header_uses_two_tone_text_wordmark(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertContains(
            response,
            '<span class="brand-split">Split</span>'
            '<span class="brand-mate">Mate</span>',
        )
