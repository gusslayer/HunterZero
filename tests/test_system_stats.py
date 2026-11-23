"""Verify the local disk-usage helper."""

import unittest
from pathlib import Path

from core.system_stats import disk_usage_percent


class DiskUsageTests(unittest.TestCase):
    """Test disk-usage bounds and robustness on real and invalid paths."""

    def test_disk_usage_percent_is_clamped_and_robust(self):
        """Return 0..100 for a real path and 0 when the path is invalid."""
        percent = disk_usage_percent(Path("."))
        self.assertIsInstance(percent, int)
        self.assertGreaterEqual(percent, 0)
        self.assertLessEqual(percent, 100)
        self.assertEqual(disk_usage_percent(Path("no-such-path-xyz")), 0)


if __name__ == "__main__":
    unittest.main()
