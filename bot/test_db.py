"""Quick self-check without Telegram token."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bot.db import DeviceDB, format_device


class DeviceDBTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DeviceDB(Path(self.tmp.name) / "t.db")
        self.owner = 42

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_list_find(self) -> None:
        did = self.db.add_device(
            self.owner,
            "iPhone 14",
            model="Apple",
            serial="SN1",
            imei="356789012345678",
            phone="9876543210",
        )
        self.assertGreater(did, 0)
        self.assertEqual(self.db.count(self.owner), 1)
        rows = self.db.search(self.owner, "iPhone")
        self.assertEqual(len(rows), 1)
        self.assertIn("iPhone 14", format_device(rows[0]))
        rows2 = self.db.search(self.owner, "356789")
        self.assertEqual(len(rows2), 1)

    def test_owner_isolation(self) -> None:
        self.db.add_device(1, "A")
        self.db.add_device(2, "B")
        self.assertEqual(self.db.count(1), 1)
        self.assertEqual(self.db.count(2), 1)
        self.assertEqual(len(self.db.search(1, "B")), 0)

    def test_get_by_device_id(self) -> None:
        did = self.db.add_device(
            self.owner,
            "iPhone 14",
            serial="SN-IPHONE-001",
            imei="356789012345678",
        )
        by_id = self.db.get_by_device_id(self.owner, str(did))
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id["name"], "iPhone 14")
        by_serial = self.db.get_by_device_id(self.owner, "SN-IPHONE-001")
        self.assertIsNotNone(by_serial)
        by_imei = self.db.get_by_device_id(self.owner, "356789012345678")
        self.assertIsNotNone(by_imei)
        missing = self.db.get_by_device_id(self.owner, "99999")
        self.assertIsNone(missing)

    def test_csv_import(self) -> None:
        sample = Path(__file__).resolve().parent.parent / "sample_data" / "devices.csv"
        n = self.db.import_file(self.owner, sample)
        self.assertEqual(n, 5)
        found = self.db.search(self.owner, "MacBook")
        self.assertEqual(len(found), 1)

    def test_json_import(self) -> None:
        sample = Path(__file__).resolve().parent.parent / "sample_data" / "devices.json"
        n = self.db.import_file(self.owner, sample)
        self.assertEqual(n, 2)
        found = self.db.search(self.owner, "Pixel")
        self.assertEqual(len(found), 1)


if __name__ == "__main__":
    unittest.main()
