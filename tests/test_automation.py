import copy
import io
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from pixelhouse.core import AutomationError, assert_current, due, plan, select_product, products
from pixelhouse.media import render_image
from pixelhouse.publishing import facebook, instagram


PRODUCT = {"id": "1", "name": "Verified camera accessory", "stock": 2, "price": 1490,
           "image": "https://pixelhouse.lk/img/item.png", "url": "https://pixelhouse.lk/single-product.html?slug=item", "category": "GoPro Accessories"}


class Store:
    def __init__(self, post):
        self.post = post
        self.saved = []
        self.fail = False
    def save(self):
        if self.fail:
            raise AutomationError("Checkpoint unavailable")
        self.saved.append(copy.deepcopy(self.post))


class FakeMeta:
    page_id = "123"
    instagram_id = "456"
    def __init__(self, callback):
        self.callback = callback
        self.calls = []
    def call(self, path, body=None):
        self.calls.append((path, body))
        return self.callback(path, body)
    def upload_reel(self, url, media):
        self.calls.append(("upload", None))
        return {"success": True}


def fixture(kind="image"):
    p = plan(copy.deepcopy(PRODUCT), date(2026, 11, 6), kind, "en")
    p["media_url"] = "https://raw.githubusercontent.com/owner/repo/commit/file.jpg"
    record = {"phase": "new", "status": "pending"}
    p["publications"] = {"test": record}
    return p, record, Store(p)


class PlanningTests(unittest.TestCase):
    def test_video_calendar_cadence_across_month(self):
        self.assertTrue(due("video", date(2026, 12, 3), "2026-11-30"))
        self.assertFalse(due("video", date(2026, 12, 2), "2026-11-30"))
        self.assertTrue(due("image", date(2026, 12, 2), "2026-11-30"))
        self.assertFalse(due("image", date(2026, 11, 29), "2026-11-30"))

    def test_stock_and_exclusion(self):
        catalog = [{**PRODUCT, "stock": None}, {**PRODUCT, "id": "2", "stock": 0}, {**PRODUCT, "id": "3"}]
        self.assertEqual(select_product(catalog, {"posts": {}}, date.today(), "image")["id"], "3")
        with self.assertRaises(AutomationError):
            select_product(catalog, {"posts": {}}, date.today(), "image", ["3"])

    def test_avoids_recent_products(self):
        state = {"posts": {"old": {"slot": "2026-11-05-image", "product": PRODUCT}}}
        self.assertEqual(select_product([PRODUCT, {**PRODUCT, "id": "2"}], state, date.today(), "image")["id"], "2")

    def test_holds_price_and_stock_changes(self):
        for current in ({**PRODUCT, "price": 1590}, {**PRODUCT, "stock": 0}, {**PRODUCT, "image": "https://pixelhouse.lk/new.jpg"}):
            with self.assertRaises(AutomationError):
                assert_current(PRODUCT, [current])

    def test_unverified_price_omitted_without_discount_claim(self):
        p = plan({**PRODUCT, "price": None}, date.today(), "image", "en")
        self.assertNotIn("LKR", p["caption"])
        self.assertNotIn("bestseller", p["caption"].lower())
        self.assertNotIn("off", p["caption"].lower())

    def test_fractional_price_not_rounded(self):
        self.assertIn("1,490.25", plan({**PRODUCT, "price": 1490.25}, date.today(), "image", "en")["caption"])

    def test_source_rejects_unknown_stock_and_non_numeric_prices(self):
        raw = {"products": [{"id": 3, "slug": "x", "name": "Item", "image": "img/x.jpg", "stock": "4", "price": "call for price"}]}
        with patch("pixelhouse.core.json_request", return_value=raw):
            imported = products()
        self.assertIsNone(imported[0]["stock"])
        self.assertIsNone(imported[0]["price"])

    def test_changed_catalog_schema_fails_closed(self):
        with patch("pixelhouse.core.json_request", return_value={"items": []}):
            with self.assertRaises(AutomationError):
                products()


class PublisherTests(unittest.TestCase):
    def test_checkpoint_failure_prevents_any_platform_call(self):
        post, rec, store = fixture()
        store.fail = True
        meta = FakeMeta(lambda p, b: {"id": "never"})
        with self.assertRaises(AutomationError):
            facebook(post, rec, meta, store, lambda: None)
        self.assertEqual(meta.calls, [])

    def test_facebook_success_is_not_replayed(self):
        post, rec, store = fixture()
        meta = FakeMeta(lambda p, b: {"id": "photo1", "post_id": "post1"})
        facebook(post, rec, meta, store, lambda: None)
        facebook(post, rec, meta, store, lambda: None)
        self.assertEqual(len(meta.calls), 1)
        self.assertEqual(rec["status"], "published")
        self.assertEqual(store.saved[0]["publications"]["test"]["phase"], "photo_request")

    def test_ambiguous_facebook_timeout_cannot_duplicate(self):
        post, rec, store = fixture()
        def fail(path, body):
            raise AutomationError("Timeout after possible remote acceptance")
        meta = FakeMeta(fail)
        with self.assertRaises(AutomationError):
            facebook(post, rec, meta, store, lambda: None)
        with self.assertRaises(AutomationError):
            facebook(post, rec, meta, store, lambda: None)
        self.assertEqual(len(meta.calls), 1)
        self.assertEqual(rec["status"], "uncertain")

    def test_instagram_resumes_one_container_and_one_publish(self):
        post, rec, store = fixture()
        statuses = iter(["IN_PROGRESS", "FINISHED"])
        def answer(path, body):
            if path.endswith("/media"):
                return {"id": "container"}
            if path.endswith("/media_publish"):
                return {"id": "published"}
            if "fields=status" in path:
                return {"status_code": next(statuses)}
            return {"permalink": "https://www.instagram.com/p/real/"}
        meta = FakeMeta(answer)
        with self.assertRaises(AutomationError):
            instagram(post, rec, meta, store, lambda: None, poll_seconds=0, max_polls=1)
        instagram(post, rec, meta, store, lambda: None, poll_seconds=0)
        instagram(post, rec, meta, store, lambda: None, poll_seconds=0)
        self.assertEqual(sum(p.endswith("/media") for p, _ in meta.calls), 1)
        self.assertEqual(sum(p.endswith("/media_publish") for p, _ in meta.calls), 1)
        self.assertEqual(rec["status"], "published")

    def test_lost_instagram_publish_response_reconciles_without_replay(self):
        post, rec, store = fixture()
        rec.update(phase="publish_request", container_id="container")
        meta = FakeMeta(lambda p, b: {"status_code": "PUBLISHED"})
        instagram(post, rec, meta, store, lambda: None)
        self.assertEqual(rec["status"], "published")
        self.assertTrue(all(b is None for _, b in meta.calls))

    def test_uncertain_instagram_finished_is_not_republished(self):
        post, rec, store = fixture()
        rec.update(phase="publish_request", container_id="container")
        meta = FakeMeta(lambda p, b: {"status_code": "FINISHED"})
        with self.assertRaises(AutomationError):
            instagram(post, rec, meta, store, lambda: None)
        self.assertEqual(rec["status"], "uncertain")
        self.assertTrue(all(b is None for _, b in meta.calls))

    def test_instagram_revalidates_before_final_publish(self):
        post, rec, store = fixture()
        rec.update(phase="container_created", container_id="container")
        meta = FakeMeta(lambda p, b: {"status_code": "FINISHED"})
        def invalid():
            raise AutomationError("Price changed")
        with self.assertRaises(AutomationError):
            instagram(post, rec, meta, store, invalid)
        self.assertTrue(all(b is None for _, b in meta.calls))

    def test_facebook_reel_stages_and_publication_confirmation(self):
        post, rec, store = fixture("video")
        polls = 0
        def answer(path, body):
            nonlocal polls
            if body and body.get("upload_phase") == "start":
                return {"video_id": "video1", "upload_url": "https://rupload.facebook.com/video-upload/video1"}
            if body:
                return {"success": True}
            polls += 1
            return {"status": {"video_status": "ready", "publishing_phase": {"publish_status": "published" if polls > 1 else "draft"}}}
        meta = FakeMeta(answer)
        facebook(post, rec, meta, store, lambda: None, poll_seconds=0)
        facebook(post, rec, meta, store, lambda: None)
        self.assertEqual(rec["status"], "published")
        self.assertEqual(sum(b is not None and b.get("upload_phase") == "start" for _, b in meta.calls), 1)
        self.assertEqual(sum(b is not None and b.get("upload_phase") == "finish" for _, b in meta.calls), 1)
        self.assertEqual(sum(p == "upload" for p, _ in meta.calls), 1)

    def test_media_renders_jpeg_with_platform_dimensions(self):
        source = io.BytesIO()
        Image.new("RGB", (500, 500), "gray").save(source, "PNG")
        post, _, _ = fixture()
        with TemporaryDirectory() as temp:
            result = render_image(post, temp, source.getvalue())
            for variant, size in (("feed", (1080, 1350)), ("vertical", (1080, 1920))):
                with Image.open(result[variant]) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, size)


if __name__ == "__main__":
    unittest.main()
