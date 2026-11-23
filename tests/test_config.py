import json
import tempfile
import unittest
from pathlib import Path

from core.config import AppSettings


class AppSettingsTests(unittest.TestCase):
    def test_missing_file_uses_documented_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = AppSettings.load(Path(temporary) / "missing.json")

        self.assertEqual(settings.stats_interval_seconds, 2)
        self.assertEqual(settings.heartbeat_interval_seconds, 5)

    def test_rejects_out_of_range_interval(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            path.write_text(json.dumps({"heartbeat_interval_seconds": 0}), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                AppSettings.load(path)


if __name__ == "__main__":
    unittest.main()
