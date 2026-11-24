"""Verify the DNS module's validation, argv building, parsing, and navigation."""

import unittest
from pathlib import Path

import pygame

import yaml

from core import theme
from core.hostname import normalize_hostname
from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.system_stats import StatsReader
from modules.nslookup.main import build_nslookup_command, parse_addresses
from modules.nslookup.screen import NsLookupScreen


ROOT = Path(__file__).resolve().parents[1]


class FakeProcessManager:
    """Capture a requested DNS command without launching a real process."""

    def __init__(self) -> None:
        """Start with empty command history and no active child."""
        self.message = ""
        self.output = ""
        self.running = None
        self.commands = []
        self.started = True

    def start_command(self, label, command, timeout):
        """Record the validated argv and simulate a running child."""
        self.commands.append((label, command, timeout))
        self.running = object()
        self.message = f"Ejecutando {label}"
        return self.started

    def stop(self):
        """Simulate cancellation of the active command."""
        self.running = None
        self.message = "Cancelado"


class NsLookupTests(unittest.TestCase):
    """Exercise hostname editing, query building, and result parsing offline."""

    def test_manifest_declares_module_metadata(self):
        """Require a valid manifest with an available icon for the DNS module."""
        path = ROOT / "modules" / "nslookup" / "manifest.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "nslookup")
        self.assertEqual(data["screen"], "screen.py")
        self.assertIn("dnsutils", data["deps"])
        self.assertTrue((ROOT / "assets" / "icons" / f"{data['icon']}.png").is_file())

    def test_hostname_validation_rejects_unsafe_input(self):
        """Accept DNS names but reject spaces, symbols, and oversized labels."""
        self.assertEqual(normalize_hostname(" Example.COM "), "example.com")
        self.assertEqual(normalize_hostname("a-b.example.co.uk"), "a-b.example.co.uk")
        for bad in ("", "bad host", "http://x.com", "a..b", "-bad.com", "a" * 64 + ".com"):
            with self.assertRaises(ValueError):
                normalize_hostname(bad)

    def test_command_builder_uses_only_validated_argv(self):
        """Build a bounded nslookup argv and reject unsupported record types."""
        self.assertEqual(
            build_nslookup_command("Example.com", "A"),
            ["nslookup", "-type=A", "example.com"],
        )
        self.assertEqual(
            build_nslookup_command("example.com", "AAAA"),
            ["nslookup", "-type=AAAA", "example.com"],
        )
        with self.assertRaises(ValueError):
            build_nslookup_command("example.com", "ANY")
        with self.assertRaises(ValueError):
            build_nslookup_command("bad host", "A")

    def test_parse_addresses_only_reads_answers(self):
        """Extract unique answer IPs while ignoring the resolver's own address."""
        output = (
            "Server:\t\t192.168.1.1\n"
            "Address:\t192.168.1.1#53\n"
            "\n"
            "Non-authoritative answer:\n"
            "Name:\texample.com\n"
            "Address: 93.184.216.34\n"
            "Name:\texample.com\n"
            "Address: 93.184.216.34\n"
        )
        self.assertEqual(parse_addresses(output), ["93.184.216.34"])

    def test_screen_edits_host_and_runs_a_confirmed_query(self):
        """Navigate the editor, confirm the query, and parse the finished result."""
        screen = NsLookupScreen()
        processes = FakeProcessManager()
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "edit_host")
        for _ in range(10):
            screen.handle(RIGHT, processes)
        screen.handle(DOWN, processes)
        self.assertEqual(screen.editor.value, "example.col")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "settings")
        screen.handle(DOWN, processes)
        screen.handle(RIGHT, processes)
        self.assertEqual(screen.record_type, 1)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "confirm")
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "running")
        self.assertEqual(
            processes.commands[0][1], ["nslookup", "-type=AAAA", "example.col"]
        )
        processes.running = None
        processes.output = "Name: example.col\nAddress: 2001:db8::1\n"
        screen.sync(processes)
        self.assertEqual(screen.phase, "result")
        self.assertEqual(screen.addresses, ["2001:db8::1"])
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "settings")
        self.assertTrue(screen.handle(BACK, processes))

    def test_screen_can_cancel_the_editor_and_the_query(self):
        """B restores the previous host and cancels a running lookup."""
        screen = NsLookupScreen()
        processes = FakeProcessManager()
        screen.handle(OPEN, processes)
        screen.handle(UP, processes)
        screen.handle(BACK, processes)
        self.assertEqual(screen.editor.value, "example.com")
        screen.handle(DOWN, processes)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "running")
        screen.handle(BACK, processes)
        self.assertEqual(screen.phase, "result")
        self.assertIsNone(processes.running)

    def test_screen_renders_in_memory(self):
        """Draw every phase of the DNS screen without a window or network."""
        pygame.init()
        surface = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        screen = NsLookupScreen()
        processes = FakeProcessManager()
        font = theme.load_font(8)
        title_font = theme.load_font(16)
        stats = StatsReader().read()
        for phase in ("settings", "edit_host", "confirm", "running", "result", "help"):
            screen.phase = phase
            screen.draw(surface, title_font, font, font, processes, stats)
            self.assertTrue(screen.footer_hints())
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
