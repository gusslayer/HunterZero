"""Verify Ping accepts any IPv4 target and builds bounded commands."""

import unittest

from modules.ping.main import build_ping_command, validate_target


class PingCommandTests(unittest.TestCase):
    """Test safe Ping argument construction without sending network traffic."""

    def test_any_single_ipv4_target_is_allowed(self):
        """Accept private and public IPv4, rejecting other target forms."""
        for target in ("192.168.1.1", "10.0.0.2", "8.8.8.8", "203.0.113.7"):
            with self.subTest(target=target):
                self.assertEqual(validate_target(target), target)
        for target in ("example.com", "192.168.1.0/24", "192.168.1.1;id", "::1"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_target(target)

    def test_ping_command_has_a_small_fixed_packet_limit(self):
        """Generate fixed Linux ping flags and reject unsupported packet counts."""
        self.assertEqual(
            build_ping_command("8.8.8.8", 2),
            ["ping", "-n", "-c", "2", "-W", "2", "8.8.8.8"],
        )
        with self.assertRaises(ValueError):
            build_ping_command("192.168.1.1", 10)


if __name__ == "__main__":
    unittest.main()
