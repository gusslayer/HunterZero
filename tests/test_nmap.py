"""Verify the Nmap command is restricted to conservative TCP-connect scans."""

import unittest

from modules.nmap.main import build_nmap_command, validate_target


class NmapCommandTests(unittest.TestCase):
    """Test Nmap argv construction without scanning a live device."""

    def test_only_private_ipv4_targets_are_allowed(self):
        """Reject targets outside a manually specified RFC1918 IPv4 address."""
        self.assertEqual(validate_target("10.0.0.2"), "10.0.0.2")
        with self.assertRaises(ValueError):
            validate_target("203.0.113.1")

    def test_command_is_unprivileged_slow_and_limited_to_common_ports(self):
        """Build a bounded TCP-connect command and reject arbitrary port limits."""
        command = build_nmap_command("10.0.0.2", 50)
        self.assertEqual(
            command,
            [
                "nmap", "-n", "-Pn", "-sT", "-T2",
                "--top-ports", "50", "--open", "--host-timeout", "90s",
                "10.0.0.2",
            ],
        )
        self.assertNotIn("-sS", command)
        with self.assertRaises(ValueError):
            build_nmap_command("10.0.0.2", 1000)
