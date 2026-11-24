"""Verify the Nmap command is restricted to conservative TCP-connect scans with NSE vuln scripts."""

import unittest

from core.process_manager import MAX_COMMAND_TIMEOUT_SECONDS
from modules.nmap.main import build_nmap_command, validate_target
from modules.nmap.screen import NmapScreen


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
                "--script", "vuln",
                "10.0.0.2",
            ],
        )
        self.assertNotIn("-sS", command)
        with self.assertRaises(ValueError):
            build_nmap_command("10.0.0.2", 1000)

    def test_screen_timeout_is_accepted_by_the_process_launcher(self):
        """Keep Nmap's GUI timeout inside the launcher's allowed range."""
        screen = NmapScreen()
        self.assertLessEqual(
            screen.timeout_for_parameter(next(iter(screen.parameter_values))),
            MAX_COMMAND_TIMEOUT_SECONDS,
        )

    def test_vuln_scripts_are_included_not_scan_vuln(self):
        """Include the NSE vuln category and never the non-existent --scan-vuln."""
        command = build_nmap_command("10.0.0.2", 20)
        self.assertEqual(command[command.index("--script") + 1], "vuln")
        self.assertNotIn("--scan-vuln", command)
