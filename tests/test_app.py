"""Verify the kiosk app never closes itself while the GPi is running."""

import unittest
from unittest.mock import patch

from core.app import HunterZeroApp
from core.input import QUIT


class FakeMenu:
    """Minimal menu controller that records navigation back to the module list."""

    def __init__(self) -> None:
        """Start with a module open so a quit event has somewhere to return."""
        self.active_plugin = object()
        self.back_calls = 0

    def back(self) -> None:
        """Close the active module and count the navigation."""
        self.active_plugin = None
        self.back_calls += 1


class AppLifecycleTests(unittest.TestCase):
    """Guard the event paths that could blank the GPi framebuffer."""

    def test_sdl_quit_returns_to_menu_without_stopping_the_app(self):
        """Treat SDL_QUIT as navigation back, never as an application exit."""
        app = object.__new__(HunterZeroApp)
        app.running = True
        app.menu = FakeMenu()
        app.tool_screen = object()
        with patch("core.app.pygame.event.get", return_value=[object()]), patch(
            "core.app.action_from_event", return_value=QUIT
        ):
            app._events()
        self.assertTrue(app.running)
        self.assertIsNone(app.tool_screen)
        self.assertEqual(app.menu.back_calls, 1)


if __name__ == "__main__":
    unittest.main()
