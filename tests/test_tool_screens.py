"""Verify that each tool has a separate, gamepad-driven command flow."""

import unittest

import pygame

from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.icons import load_icon
from modules.nmap.screen import NmapScreen
from modules.ping.screen import PingScreen
from modules.system_monitor.screen import SystemMonitorScreen
from core.system_stats import StatsReader


class FakeProcessManager:
    """Capture a requested command without starting a real network process."""

    def __init__(self):
        """Initialize fake process state and an empty command history."""
        self.message = ""
        self.output = ""
        self.running = None
        self.commands = []

    def start_command(self, label, command, timeout):
        """Record a command request and simulate a running child."""
        self.commands.append((label, command, timeout))
        self.running = object()
        self.message = f"Ejecutando {label}"
        return True

    def stop(self):
        """Simulate cancellation of the active command."""
        self.running = None
        self.message = "Cancelado"


class ToolScreenTests(unittest.TestCase):
    """Exercise manual target entry and confirmation for each independent tool."""

    def test_menu_icon_assets_exist_and_load(self):
        """Require every manifest icon name to have a usable PNG asset."""
        pygame.init()
        for name in (
            "activity", "battery-charging", "bell", "chart",
            "chart-no-axes-combined", "code", "code-xml", "cpu",
            "crosshair", "database", "download", "eye", "folder",
            "gauge", "hard-drive", "lock", "map-pin", "memory-stick",
            "network", "play", "power", "radar", "radio", "rotate-cw",
            "scan-line", "search", "server", "settings", "shield-check",
            "system", "terminal", "upload", "wifi",
        ):
            icon = load_icon(name)
            self.assertIsNotNone(icon, f"Falta assets/icons/{name}.png")
            self.assertGreater(icon.get_width(), 0)
            self.assertGreater(icon.get_height(), 0)
        pygame.quit()

    def test_ping_manual_ip_and_confirmation_use_only_gamepad_actions(self):
        """Edit an IPv4 octet, confirm Ping, and verify only its own command starts."""
        screen = PingScreen()
        processes = FakeProcessManager()
        screen.handle(OPEN, processes)
        screen.handle(RIGHT, processes)
        screen.handle(RIGHT, processes)
        screen.handle(UP, processes)
        screen.handle(OPEN, processes)

        self.assertEqual(screen.target.address, "192.168.2.1")
        screen.handle(DOWN, processes)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "confirm")
        screen.handle(BACK, processes)
        self.assertEqual(processes.commands, [])
        screen.handle(OPEN, processes)
        screen.handle(OPEN, processes)

        self.assertEqual(processes.commands[0][1][0], "ping")
        self.assertIn("192.168.2.1", processes.commands[0][1])

    def test_nmap_has_an_independent_scan_and_cancellable_process_flow(self):
        """Confirm Nmap, verify its own executable, and cancel with the B action."""
        screen = NmapScreen()
        processes = FakeProcessManager()
        screen.handle(OPEN, processes)
        screen.handle(RIGHT, processes)
        screen.handle(RIGHT, processes)
        screen.handle(UP, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.target.address, "192.168.2.1")
        screen.handle(DOWN, processes)
        screen.handle(RIGHT, processes)
        self.assertEqual(screen.parameter, 50)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        screen.handle(OPEN, processes)

        self.assertEqual(processes.commands[0][1][0], "nmap")
        self.assertIn("--top-ports", processes.commands[0][1])
        self.assertIn("50", processes.commands[0][1])
        self.assertIn("192.168.2.1", processes.commands[0][1])
        self.assertIn("--script", processes.commands[0][1])
        self.assertEqual(screen.phase, "running")
        screen.handle(BACK, processes)

        self.assertIsNone(processes.running)
        self.assertEqual(screen.phase, "result")

    def test_help_is_accessible_and_back_exits_with_gamepad_only(self):
        """Open shared help from the options and return to the module menu."""
        screen = PingScreen()
        processes = FakeProcessManager()
        for _ in range(3):
            screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "help")
        self.assertTrue(screen.handle(BACK, processes))

    def test_parameter_options_cycle_with_left_and_right(self):
        """Keep Ping and Nmap parameter ranges separate and configurable."""
        ping = PingScreen()
        nmap = NmapScreen()
        processes = FakeProcessManager()
        ping.handle(DOWN, processes)
        ping.handle(RIGHT, processes)
        nmap.handle(DOWN, processes)
        nmap.handle(RIGHT, processes)

        self.assertEqual(ping.parameter, 3)
        self.assertEqual(nmap.parameter, 50)

    def test_screens_render_without_a_window_or_keyboard(self):
        """Render each screen to an in-memory GPi-sized surface."""
        pygame.init()
        surface = pygame.Surface((640, 480))
        title_font = pygame.font.Font(None, 18)
        body_font = pygame.font.Font(None, 14)
        small_font = pygame.font.Font(None, 12)
        processes = FakeProcessManager()

        stats = StatsReader().read()
        PingScreen().draw(surface, title_font, body_font, small_font, processes, stats)
        NmapScreen().draw(surface, title_font, body_font, small_font, processes, stats)
        monitor = SystemMonitorScreen()
        monitor.draw(surface, title_font, body_font, small_font, processes, stats)
        monitor.handle(OPEN, processes)
        monitor.draw(surface, title_font, body_font, small_font, processes, stats)

        self.assertEqual(surface.get_size(), (640, 480))
        pygame.quit()
