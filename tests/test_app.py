"""Verify the kiosk app never closes itself while the GPi is running."""

import unittest
from unittest.mock import patch

from core.app import HunterZeroApp, _hide_mouse_cursor
from core.input import OPEN, QUIT, RUN


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


class FakeProcesses:
    """Minimal process manager that records cancellation requests."""

    def __init__(self) -> None:
        """Start with no cancellation recorded."""
        self.stopped = False

    def stop(self) -> None:
        """Record that running child processes were stopped."""
        self.stopped = True


class FakeToolScreen:
    """Minimal module screen that records the actions it receives."""

    def __init__(self) -> None:
        """Start with an empty action history and no close calls."""
        self.actions = []
        self.close_calls = 0

    def handle(self, action, processes) -> bool:
        """Record one action and keep the module open."""
        del processes
        self.actions.append(action)
        return False

    def close(self) -> None:
        """Record that the app asked this screen to stop its background work."""
        self.close_calls += 1


class AppLifecycleTests(unittest.TestCase):
    """Guard the event paths that could blank the GPi framebuffer."""

    def test_sdl_cursor_is_hidden(self):
        """Disable SDL's mouse cursor so no pointer is drawn over the UI."""
        with patch("core.app.pygame.mouse.set_visible") as set_visible:
            _hide_mouse_cursor()
        set_visible.assert_called_once_with(False)

    def test_start_inside_a_module_confirms_like_a(self):
        """Forward START as OPEN so module screens are not dead ends."""
        app = object.__new__(HunterZeroApp)
        app.menu = FakeMenu()
        app.tool_screen = FakeToolScreen()
        app.processes = object()
        app._handle_plugin_action(RUN)
        self.assertEqual(app.tool_screen.actions, [OPEN])

    def test_sdl_quit_returns_to_menu_without_stopping_the_app(self):
        """Treat SDL_QUIT as navigation back, never as an application exit."""
        app = object.__new__(HunterZeroApp)
        app.running = True
        app.menu = FakeMenu()
        app.tool_screen = object()
        app.processes = FakeProcesses()
        with patch("core.app.pygame.event.get", return_value=[object()]), patch(
            "core.app.action_from_event", return_value=QUIT
        ):
            app._events()
        self.assertTrue(app.running)
        self.assertIsNone(app.tool_screen)
        self.assertEqual(app.menu.back_calls, 1)
        self.assertTrue(app.processes.stopped)

    def test_leaving_a_screen_closes_its_background_work(self):
        """Ask module screens to cancel their jobs before dropping the reference."""
        app = object.__new__(HunterZeroApp)
        app.menu = FakeMenu()
        screen = FakeToolScreen()
        app.tool_screen = screen
        app._close_tool_screen()
        self.assertEqual(screen.close_calls, 1)
        self.assertIsNone(app.tool_screen)


if __name__ == "__main__":
    unittest.main()
