"""Verify that Ping accepts only bounded local targets and packet counts."""

import unittest

from modules.ping.main import build_ping_command, validate_target


class PingCommandTests(unittest.TestCase):
    """Test safe Ping argument construction without sending network traffic."""

    def test_only_private_ipv4_targets_are_allowed(self):
        """Reject domains, public IPs, IPv6, network ranges, and shell text."""
        self.assertEqual(validate_target("192.168.1.1"), "192.168.1.1")
        for target in ("example.com", "8.8.8.8", "192.168.1.0/24", "192.168.1.1;id", "::1"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_target(target)

    def test_ping_command_has_a_small_fixed_packet_limit(self):
        """Generate fixed Linux ping flags and reject unsupported packet counts."""
        self.assertEqual(
            build_ping_command("192.168.1.1", 2),
            ["ping", "-n", "-c", "2", "-W", "2", "192.168.1.1"],
        )
        with self.assertRaises(ValueError):
            build_ping_command("192.168.1.1", 99)
