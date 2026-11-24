"""Verify local disk, IP, and SSID helpers used by the HUD and system monitor."""

import unittest
from pathlib import Path
from unittest.mock import patch

from core.system_stats import StatsReader, disk_usage_percent, local_ip_address, wireless_ssid


class DiskUsageTests(unittest.TestCase):
    """Test disk-usage bounds and robustness on real and invalid paths."""

    def test_disk_usage_percent_is_clamped_and_robust(self):
        """Return 0..100 for a real path and 0 when the path is invalid."""
        percent = disk_usage_percent(Path("."))
        self.assertIsInstance(percent, int)
        self.assertGreaterEqual(percent, 0)
        self.assertLessEqual(percent, 100)
        self.assertEqual(disk_usage_percent(Path("no-such-path-xyz")), 0)


class NetworkStatsTests(unittest.TestCase):
    """Test the read-only helpers that report the equipment's network identity."""

    def test_local_ip_address_uses_the_route_to_the_internet(self):
        """Return the selected local address without sending UDP traffic."""
        with patch("core.system_stats.socket.socket") as socket_factory:
            socket = socket_factory.return_value.__enter__.return_value
            socket.getsockname.return_value = ("192.168.1.42", 12345)
            self.assertEqual(local_ip_address(), "192.168.1.42")
            socket.connect.assert_called_once_with(("8.8.8.8", 80))

    def test_local_ip_address_is_unknown_without_a_route(self):
        """Report N/D instead of crashing when no outbound route exists."""
        with patch("core.system_stats.socket.socket", side_effect=OSError("no route")):
            self.assertEqual(local_ip_address(), "N/D")

    def test_wireless_ssid_reads_iw_output(self):
        """Extract the SSID from the connected wireless interface."""
        with patch("core.system_stats._wireless_interfaces", return_value=["wlan0"]), patch(
            "core.system_stats.subprocess.run"
        ) as run:
            run.return_value.stdout = "BSS 00:11:22:33:44:55\nmode: station\nSSID: MiWiFi\n"
            self.assertEqual(wireless_ssid(), "MiWiFi")

    def test_stats_reader_caches_network_identity(self):
        """Reuse the IP and SSID between refreshes to avoid spawning commands."""
        reader = StatsReader()
        with patch("core.system_stats.local_ip_address", return_value="10.0.0.7") as ip, patch(
            "core.system_stats.wireless_ssid", return_value="Talleres"
        ) as ssid, patch("core.system_stats.time.monotonic", return_value=100.0):
            first = reader.read()
            second = reader.read()
        self.assertEqual(first.local_ip, "10.0.0.7")
        self.assertEqual(second.ssid, "Talleres")
        ip.assert_called_once_with()
        ssid.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
