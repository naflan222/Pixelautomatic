import copy
import os
import unittest
from datetime import date
from unittest.mock import Mock, patch

from pixelhouse.core import AutomationError, automation_enabled
import run


CONFIG = {"state_branch": "automation-state", "platforms": ["facebook", "instagram"],
          "brand_approved": True, "photo_rights_confirmed": True,
          "automation_enabled": True, "start_date": "2026-11-07"}


class ActivationTests(unittest.TestCase):
    def stores(self):
        store = Mock()
        store.branch_exists = True
        store.load.return_value = {"version": 1, "posts": {}}
        return store

    def test_repository_pause_overrides_enabled_config_before_meta_is_contacted(self):
        with patch.dict(os.environ, {"AUTOMATION_ENABLED": "false"}), patch("run.load_config", return_value=CONFIG), patch("run.GitHubStore", return_value=self.stores()), patch("run.meta_from_env") as meta:
            with self.assertRaisesRegex(AutomationError, "Publishing is disabled"):
                run.main(["publish"])
        meta.assert_not_called()

    def test_config_pause_blocks_publishing_without_repository_variable(self):
        config = {**CONFIG, "automation_enabled": False}
        with patch.dict(os.environ, {"AUTOMATION_ENABLED": ""}), patch("run.load_config", return_value=config), patch("run.GitHubStore", return_value=self.stores()), patch("run.meta_from_env") as meta:
            with self.assertRaisesRegex(AutomationError, "Publishing is disabled"):
                run.main(["publish"])
        meta.assert_not_called()

    def test_enabled_config_resumes_without_reposting_a_completed_slot(self):
        store = self.stores()
        store.load.return_value["posts"]["2026-11-07-image"] = {"publications": {p: {"status": "published"} for p in CONFIG["platforms"]}}
        with patch.dict(os.environ, {"AUTOMATION_ENABLED": ""}), patch("run.load_config", return_value=CONFIG), patch("run.local_day", return_value=date(2026, 11, 7)), patch("run.GitHubStore", return_value=store), patch("run.meta_from_env") as meta, patch("run.render") as render, patch("run.publish_platforms") as publish, patch("run.summary"):
            run.main(["publish"])
        meta.return_value.check.assert_called_once_with(CONFIG["platforms"])
        render.assert_not_called()
        publish.assert_not_called()
        store.save.assert_not_called()

    def test_connection_check_still_works_while_publishing_is_paused(self):
        config = {**CONFIG, "automation_enabled": False}
        with patch.dict(os.environ, {"AUTOMATION_ENABLED": "false"}), patch("run.load_config", return_value=config), patch("run.GitHubStore", return_value=self.stores()), patch("run.meta_from_env") as meta, patch("run.products", return_value=[{"stock": 1}]), patch("run.summary"):
            meta.return_value.check.return_value = {"page": "Fixture Page"}
            run.main(["check"])
        meta.return_value.check.assert_called_once_with(CONFIG["platforms"])

    def test_invalid_repository_switch_does_not_fall_through_to_enabled_config(self):
        with self.assertRaises(AutomationError):
            automation_enabled(CONFIG, "not-a-valid-switch")

    def test_old_configs_without_a_switch_stay_paused(self):
        self.assertFalse(automation_enabled({}, ""))
        self.assertFalse(automation_enabled({"automation_enabled": "false"}, ""))


if __name__ == "__main__":
    unittest.main()
