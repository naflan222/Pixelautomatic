import copy
import io
import unittest
from datetime import date, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from pixelhouse.core import AutomationError
from pixelhouse.content import DEFAULT_ROTATION, TOPICS, TIPS, EXPLAINERS, EXPLODED, build_plan, rotation_topic, fallback_to_tip, _choose, editorial_post
from pixelhouse.editorial_media import render_editorial
from pixelhouse.publishing import instagram, facebook
from test_automation import FakeMeta, Store, PRODUCT
from run import validate_before_publish

CONFIG = {"start_date": "2026-11-07", "content_rotation": DEFAULT_ROTATION,
          "language": "en", "excluded_product_ids": [], "ai_image": {"provider": "local_cpu", "timeout_seconds": 900}}
DAY = date(2026, 11, 7)
EMPTY = {"posts": {}}


class GrowthPlanningTests(unittest.TestCase):
    def test_seven_day_rotation_includes_all_six_requested_categories(self):
        topics=[rotation_topic(CONFIG, DAY+timedelta(days=i), "image") for i in range(7)]
        self.assertEqual(topics, DEFAULT_ROTATION)
        self.assertEqual(set(topics), set(TOPICS))

    def test_same_day_video_uses_a_different_content_category(self):
        for i in range(7):
            day=DAY+timedelta(days=i)
            self.assertNotEqual(rotation_topic(CONFIG,day,"image"),rotation_topic(CONFIG,day,"video"))

    def test_old_product_only_configs_keep_their_existing_behavior(self):
        self.assertEqual(rotation_topic({"start_date":"2026-11-07"},DAY,"image"),"product")

    def test_non_product_topics_do_not_depend_on_the_store_being_online(self):
        for topic in ("camera_tip","travel","camera_explainer","exploded_view"):
            with self.subTest(topic=topic), patch("pixelhouse.content.products",side_effect=AssertionError("Catalog should not be used")):
                post=build_plan(CONFIG,EMPTY,DAY,"image",topic)
                self.assertIsNone(post["product"])
                self.assertEqual(post["topic"],topic)
                self.assertIn("pixelhouse.lk",post["caption"])
                self.assertNotIn("https://",post["caption"])
                self.assertNotIn("LKR",post["caption"])
                self.assertLessEqual(len(post["caption"]),2200)

    def test_accessory_explanation_filters_out_camera_bodies(self):
        camera={**PRODUCT,"id":"camera","category":"Action Cameras"}
        accessory={**PRODUCT,"id":"accessory","category":"GoPro Accessories"}
        with patch("pixelhouse.content.products",return_value=[camera,accessory]):
            post=build_plan(CONFIG,EMPTY,DAY,"image","accessory_explainer")
        self.assertEqual(post["product"]["id"],"accessory")
        self.assertNotIn("LKR",post["caption"])

    def test_travel_is_disclosed_as_generated_instead_of_real_location_footage(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","travel")
        self.assertTrue(p["ai_generated"])
        self.assertIn("AI-generated",p["caption"])
        self.assertIn("not a photograph of an actual location",p["caption"])
        self.assertIn(p["destination"]["name"],p["lesson"]["summary"])

    def test_exploded_views_never_claim_to_be_model_specific_teardowns(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","exploded_view")
        self.assertIn("Conceptual",p["caption"])
        self.assertIn("not to scale",p["caption"])
        self.assertIn("not a repair guide",p["caption"])
        self.assertFalse(p["ai_generated"])

    def test_library_rotation_prefers_unused_topics(self):
        state={"posts":{"old":{"slot":"2026-11-06-image","topic":"camera_tip","creative_id":TIPS[0]["id"]}}}
        item=_choose(TIPS,state,"camera_tip",DAY,"image")
        self.assertNotEqual(item["id"],TIPS[0]["id"])

    def test_failed_generation_fallback_keeps_publication_history_and_removes_ai_claim(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","travel")
        p["publications"]={"facebook":{"phase":"new","status":"pending"}}
        history=p["publications"]
        fallback_to_tip(p,"Provider unavailable")
        self.assertEqual(p["topic"],"camera_tip")
        self.assertEqual(p["requested_topic"],"travel")
        self.assertIs(p["publications"],history)
        self.assertFalse(p["ai_generated"])
        self.assertNotIn("AI-generated Sri Lanka",p["caption"])

    def test_non_product_publish_validation_never_fetches_fake_product_information(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","camera_tip")
        with patch("run.products",side_effect=AssertionError("No product facts needed")):
            validate_before_publish(p)

    def test_missing_ai_disclosure_blocks_publishing(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","travel")
        p["caption"]="A real morning in Sri Lanka."
        with self.assertRaisesRegex(AutomationError,"disclosure"):
            validate_before_publish(p)


class GrowthMediaTests(unittest.TestCase):
    def test_all_editorial_types_render_feed_and_vertical_jpegs(self):
        source=io.BytesIO();Image.new("RGB",(800,800),"gray").save(source,"PNG")
        for topic in ("camera_tip","camera_explainer","exploded_view","travel","accessory_explainer"):
            with self.subTest(topic=topic), TemporaryDirectory() as temp, patch("pixelhouse.content.products",return_value=[PRODUCT]):
                p=build_plan(CONFIG,EMPTY,DAY,"image",topic)
                images=render_editorial(p,temp,source.getvalue(),Image.new("RGB",(512,768),"seagreen") if topic=="travel" else None)
                for name,size in (("feed",(1080,1350)),("vertical",(1080,1920))):
                    with Image.open(images[name]) as picture:
                        self.assertEqual(picture.size,size)
                        self.assertEqual(picture.format,"JPEG")

    def test_ai_failure_renders_an_honestly_labeled_educational_fallback(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","travel")
        with TemporaryDirectory() as temp, patch("pixelhouse.editorial_media._scene",side_effect=AutomationError("Temporary failure")):
            images=render_editorial(p,temp)
            self.assertTrue(images["feed"].exists())
        self.assertEqual(p["topic"],"camera_tip")
        self.assertFalse(p["ai_generated"])

    def test_educational_images_vary_across_dates_for_duplicate_prevention(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","exploded_view")
        q=copy.deepcopy(p);q["date"]="2026-11-08"
        with TemporaryDirectory() as a,TemporaryDirectory() as b:
            self.assertNotEqual(render_editorial(p,a)["fingerprint"],render_editorial(q,b)["fingerprint"])

    def test_all_reviewed_lessons_render_without_truncating_explanations(self):
        for topic, items in (("camera_tip", TIPS), ("camera_explainer", EXPLAINERS), ("exploded_view", EXPLODED)):
            for item in items:
                with self.subTest(lesson=item["id"]), TemporaryDirectory() as temp:
                    post = editorial_post(item, topic, DAY, "image", "en")
                    self.assertLessEqual(len(post["caption"]), 2200)
                    render_editorial(post, temp)

    def test_generation_subprocess_does_not_receive_social_or_repository_tokens(self):
        from pixelhouse.editorial_media import _scene
        post = build_plan(CONFIG, EMPTY, DAY, "image", "travel")
        def generate_fixture(command, **kwargs):
            self.assertNotIn("META_PAGE_ACCESS_TOKEN", kwargs["env"])
            self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
            self.assertLessEqual(kwargs["timeout"], 900)
            path = command[command.index("--output") + 1]
            picture = Image.new("RGB", (512, 768), "navy")
            from PIL import ImageDraw
            ImageDraw.Draw(picture).rectangle((0, 300, 512, 768), fill="seagreen")
            picture.save(path)
        with TemporaryDirectory() as temp, patch.dict("os.environ", {"META_PAGE_ACCESS_TOKEN":"fixture-secret", "GITHUB_TOKEN":"fixture-github-secret"}), patch("pixelhouse.editorial_media.subprocess.run", side_effect=generate_fixture):
            image = _scene(post, __import__("pathlib").Path(temp))
            self.assertEqual(image.size, (512, 768))
            self.assertIn("model", post["ai_provenance"])

    def test_facebook_reel_uses_native_ai_disclosure_for_generated_scene(self):
        p = build_plan(CONFIG, EMPTY, DAY, "video", "travel")
        p["media_url"] = "https://cdn.example/scene.mp4"
        record = {"phase":"new", "status":"pending"}
        p["publications"] = {"facebook":record}
        store = Store(p)
        polls = 0
        def answer(path, body):
            nonlocal polls
            if body and body.get("upload_phase") == "start":
                return {"video_id":"video", "upload_url":"https://rupload.facebook.com/video-upload/video"}
            if body:
                return {"success":True}
            polls += 1
            return {"status":{"video_status":"ready", "publishing_phase":{"publish_status":"published" if polls > 1 else "draft"}}}
        meta = FakeMeta(answer)
        facebook(p, record, meta, store, lambda: None, poll_seconds=0)
        finish = next(body for _,body in meta.calls if body and body.get("upload_phase") == "finish")
        self.assertIs(finish["is_ai_generated"], True)
        self.assertEqual(record["status"], "published")

    def test_instagram_receives_its_documented_ai_disclosure_parameter(self):
        p=build_plan(CONFIG,EMPTY,DAY,"image","travel");p["media_url"]="https://cdn.example/scene.jpg"
        r={"phase":"new","status":"pending"};p["publications"]={"instagram":r};store=Store(p)
        def answer(path,body):
            if path.endswith('/media'):return {"id":"container"}
            if path.endswith('/media_publish'):return {"id":"post"}
            if 'fields=status' in path:return {"status_code":"FINISHED"}
            return {"permalink":"https://www.instagram.com/p/example/"}
        meta=FakeMeta(answer)
        instagram(p,r,meta,store,lambda:None,poll_seconds=0)
        creation=next(body for path,body in meta.calls if path.endswith('/media'))
        self.assertIs(creation["is_ai_generated"],True)
        self.assertEqual(r["status"],"published")
