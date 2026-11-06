import base64
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch

from pixelhouse.core import ApiError, AutomationError, GitHubStore, request


class StateTests(unittest.TestCase):
    def make(self):
        return GitHubStore("owner/repository", "fixture-token", "automation-state")

    def test_private_media_repository_rejected(self):
        store = self.make()
        store.api = Mock(return_value={"private": True, "default_branch": "main"})
        with self.assertRaises(AutomationError):
            store.load()

    def test_absent_branch_is_not_silently_created_on_read(self):
        store = self.make()
        store.api = Mock(side_effect=[{"private": False, "default_branch": "main"}, ApiError("GitHub", 404)])
        self.assertEqual(store.load()["posts"], {})
        self.assertFalse(store.branch_exists)
        self.assertTrue(all(call.kwargs.get("method", "GET") == "GET" for call in store.api.call_args_list))

    def test_existing_branch_with_missing_ledger_holds(self):
        store = self.make()
        store.api = Mock(side_effect=[{"private": False, "default_branch": "main"}, {"object": {"sha": "existing"}}, ApiError("GitHub", 404)])
        with self.assertRaisesRegex(AutomationError, "ledger is missing"):
            store.load()

    def test_read_permission_failure_does_not_reset_state(self):
        store = self.make()
        store.api = Mock(side_effect=[{"private": False, "default_branch": "main"}, ApiError("GitHub", 403)])
        with self.assertRaises(ApiError):
            store.load()

    def test_checkpoints_use_optimistic_sha_and_do_not_serialize_tokens(self):
        store = self.make()
        store.branch_exists = True
        store.sha = "previous-file-sha"
        store.api = Mock(return_value={"content": {"sha": "next-file-sha"}})
        store.save()
        body = store.api.call_args.kwargs["body"]
        self.assertEqual(body["sha"], "previous-file-sha")
        self.assertNotIn("fixture-token", base64.b64decode(body["content"]).decode())
        self.assertEqual(store.sha, "next-file-sha")

    def test_existing_ledger_is_loaded_without_losing_history(self):
        store = self.make()
        state = {"version": 1, "posts": {"2026-11-06-image": {"publications": {"facebook": {"status": "published"}}}}}
        store.api = Mock(side_effect=[{"private": False, "default_branch": "main"}, {"object": {"sha": "branch"}}, {"sha": "file-sha", "encoding": "base64", "content": base64.b64encode(json.dumps(state).encode()).decode()}])
        self.assertEqual(store.load(), state)
        self.assertEqual(store.sha, "file-sha")

    def test_network_failure_does_not_retry_post(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError("simulated failure")
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(AutomationError):
                request("https://graph.facebook.com/v27.0/123/photos", method="POST", body={"published": True})
        self.assertEqual(opener.open.call_count, 1)

    def test_only_safe_get_network_failures_receive_bounded_retries(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError("simulated failure")
        with patch("urllib.request.build_opener", return_value=opener), patch("time.sleep"):
            with self.assertRaises(AutomationError):
                request("https://graph.facebook.com/v27.0/123?fields=status")
        self.assertEqual(opener.open.call_count, 3)


if __name__ == "__main__":
    unittest.main()
