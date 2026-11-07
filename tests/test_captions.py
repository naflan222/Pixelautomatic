import unittest
from datetime import date
from unittest.mock import patch

from pixelhouse.captions import clean_description, professional_caption, source_summary
from pixelhouse.core import AutomationError, assert_current, plan, products


PRODUCT = {"id": "1", "name": "50 in 1 Accessories Kit GoPro", "price": 8000,
           "stock": 3, "category": "GoPro Accessories",
           "image": "https://pixelhouse.lk/img/kit.jpg",
           "url": "https://pixelhouse.lk/single-product.html?slug=kit",
           "description": "Complete 50-in-1 accessory bundle for GoPro Hero cameras — mounts, straps, grips, cases and more."}


class CaptionTests(unittest.TestCase):
    def test_product_details_are_taken_from_the_supplied_source(self):
        caption = professional_caption(PRODUCT, 0, "en")
        self.assertIn(PRODUCT["description"], caption)
        self.assertIn("Price: LKR 8,000", caption)
        self.assertIn("\npixelhouse.lk\n", caption)
        self.assertNotIn(PRODUCT["url"], caption)
        self.assertNotIn("single-product.html", caption)
        self.assertNotIn("waterproof", caption.lower())
        self.assertNotIn("free shipping", caption.lower())

    def test_embedded_store_prices_and_offer_claims_cannot_override_verified_price(self):
        p = {**PRODUCT, "description": "Bestseller! Save 50%. Only LKR 3,000 with free shipping."}
        caption = professional_caption(p, 0, "en")
        self.assertIn("Price: LKR 8,000", caption)
        for claim in ("Bestseller", "50%", "3,000", "free shipping"):
            self.assertNotIn(claim, caption)

    def test_cleaning_removes_hidden_html_without_dropping_compatibility_caveats(self):
        raw = '<p>Compatible with <strong>Hero 13</strong> only.</p><script>Best seller!</script><style>hidden</style><p>Not compatible with Hero 12.</p>'
        cleaned = clean_description(raw)
        self.assertEqual(cleaned, "Compatible with Hero 13 only. Not compatible with Hero 12.")
        self.assertNotIn("Best seller", cleaned)
        self.assertNotIn("<", cleaned)

    def test_long_descriptions_are_not_truncated_into_partial_claims(self):
        text = "Designed for camera use. " + "Refer to the compatibility guide. " * 20 + "Not compatible with Hero 13."
        self.assertEqual(source_summary({**PRODUCT, "description": text}), "")

    def test_duplicate_title_does_not_invent_replacement_specifications(self):
        p = {**PRODUCT, "name": "Camera", "description": "<p>Camera.</p>"}
        caption = professional_caption(p, 0, "en")
        self.assertEqual(source_summary(p), "")
        for claim in ("4K", "8K", "waterproof", "warranty"):
            self.assertNotIn(claim, caption)

    def test_importer_preserves_clean_source_details_for_future_checks(self):
        raw = {"products": [{"id": 1, "name": "Accessory", "slug": "accessory", "image": "img/a.jpg", "price": 100, "stock": 2, "description": "<p>Fits Hero 13 only.</p>"}]}
        with patch("pixelhouse.core.json_request", return_value=raw):
            p = products()[0]
        self.assertEqual(p["description"], "Fits Hero 13 only.")

    def test_changed_product_description_holds_the_generated_claim(self):
        with self.assertRaisesRegex(AutomationError, "description changed"):
            assert_current(PRODUCT, [{**PRODUCT, "description": "Updated compatibility restriction."}])

    def test_product_links_are_omitted_in_every_caption_language(self):
        product = {**PRODUCT, "url": "https://pixelhouse.lk/" + "x" * 2200}
        for language in ("en", "si", "mixed"):
            with self.subTest(language=language):
                caption = plan(product, date(2026, 11, 7), "image", language)["caption"]
                self.assertIn("\npixelhouse.lk\n", caption)
                self.assertNotIn(product["url"], caption)
                self.assertNotIn("https://", caption)
                self.assertLessEqual(len(caption), 2200)


if __name__ == "__main__":
    unittest.main()
