"""Verify that each tool has a separate, gamepad-driven command flow."""

import unittest

import pygame

from core.input import BACK, DOWN, LEFT, OPEN, RIGHT, UP
from core.ui.nmap_screen import NmapScreen
from core.ui.ping_screen import PingScreen


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
        self.assertEqual(screen.port_count, 50)
        screen.handle(DOWN, processes)
        screen.handle(OPEN, processes)
        screen.handle(OPEN, processes)

        self.assertEqual(processes.commands[0][1][0], "nmap")
        self.assertIn("--top-ports", processes.commands[0][1])
        self.assertIn("50", processes.commands[0][1])
        self.assertIn("192.168.2.1", processes.commands[0][1])
        self.assertEqual(screen.phase, "running")
        screen.handle(BACK, processes)

        self.assertIsNone(processes.running)
        self.assertEqual(screen.phase, "result")

    def test_screens_render_without_a_window_or_keyboard(self):
        """Render each screen to an in-memory GPi-sized surface."""
        pygame.init()
        surface = pygame.Surface((640, 480))
        title_font = pygame.font.Font(None, 18)
        body_font = pygame.font.Font(None, 14)
        small_font = pygame.font.Font(None, 12)
        processes = FakeProcessManager()

        PingScreen().draw(surface, title_font, body_font, small_font, processes)
        NmapScreen().draw(surface, title_font, body_font, small_font, processes)

        self.assertEqual(surface.get_size(), (640, 480))
        pygame.quit()
