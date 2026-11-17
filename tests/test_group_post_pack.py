"""Smoke tests for the Facebook Group post pack command."""
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.group_post_pack import choose_products


class GroupPostPackTests(unittest.TestCase):
    def test_module_startup(self):
        project_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.group_post_pack", "--help"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--first-date", completed.stdout)

    def test_select_only_in_stock_priced_products(self):
        catalog = [
            {"id": "1", "name": "Out", "stock": 0, "price": 8000},
            {"id": "2", "name": "Unknown", "stock": None, "price": 1000},
            {"id": "3", "name": "No price", "stock": 1, "price": None},
            {"id": "4", "name": "Valid", "stock": 3, "price": 8000},
            {"id": "5", "name": "Excluded", "stock": 2, "price": 9000},
        ]
        from datetime import date
        result = choose_products(catalog, date(2026, 11, 18), ["5"])
        self.assertEqual([item["id"] for item in result], ["4"])


if __name__ == "__main__":
    unittest.main()
