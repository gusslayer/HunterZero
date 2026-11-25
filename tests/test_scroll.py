"""Verify that long menus, process lists, and BLEEDING lists can be scrolled."""

import unittest

import pygame

from core.input import BACK, DOWN, LEFT, OPEN, UP
from core.ui.layout import MenuLayout
from core.ui.scroll import ScrollState
from modules.bleeding.screen import BleedingScreen
from modules.proc_monitor.main import ProcessSnapshot
from modules.proc_monitor.screen import ProcMonitorScreen


class FakeProcesses:
    """No-op process manager for navigation-only tests."""

    def __init__(self) -> None:
        """Start with an empty status message."""
        self.message = ""


class FakeEngine:
    """Engine stub that supplies fixed device and service results."""

    ble_available = True
    bredr_available = True
    bredr_discovery_available = True

    def __init__(self, devices, services) -> None:
        """Store the lists returned by every snapshot."""
        self.devices = devices
        self.services = services
        self.cancelled = 0

    def snapshot(self):
        """Return a state with the configured results."""
        from modules.bleeding.engine import JobState

        return JobState(devices=self.devices, services=self.services, message="Listo")

    def cancel(self) -> None:
        """Count cancellation requests."""
        self.cancelled += 1


class ScrollTests(unittest.TestCase):
    """Exercise the shared scroll window used by every long view."""

    def test_window_keeps_the_selection_visible_at_both_ends(self):
        """Move the window down as the selection reaches the last rows."""
        view = ScrollState(count=20, capacity=5)
        self.assertEqual((view.first, view.last), (0, 5))
        for _ in range(19):
            view.move(1)
        self.assertEqual(view.selected, 19)
        self.assertEqual((view.first, view.last), (15, 20))
        view.move(1)
        self.assertEqual((view.selected, view.first), (0, 0))

    def test_shrinking_a_list_clamps_selection_and_offset(self):
        """Avoid pointing at a row that disappeared after a refresh."""
        view = ScrollState(count=20, capacity=5, selected=18, offset=15)
        view.update(3)
        self.assertEqual((view.selected, view.offset), (2, 0))
        self.assertFalse(view.can_scroll)

    def test_main_menu_rows_fit_inside_the_panel(self):
        """Draw the last module inside the menu instead of below its frame."""
        layout = MenuLayout(pygame.Rect(13, 35, 294, 126), 19, 2)
        first, last = layout.visible_range(12, 11)
        self.assertEqual((first, last), (6, 12))
        for position, _index in enumerate(range(first, last)):
            row = layout.row_rect(position)
            self.assertLessEqual(row.bottom, layout.bounds.bottom)


class ProcessListScrollTests(unittest.TestCase):
    """Guard D-pad scrolling in the process monitor."""

    @staticmethod
    def _snapshots(count: int):
        """Build enough fake processes to overflow the visible list."""
        return tuple(
            ProcessSnapshot(
                pid=100 + index,
                name=f"proc{index}",
                cpu_percent=1.0,
                memory_percent=1.0,
                elapsed="1s",
            )
            for index in range(count)
        )

    def test_down_scrolls_to_processes_below_the_first_page(self):
        """Keep selecting DOWN until the last process becomes visible."""
        screen = ProcMonitorScreen()
        screen.processes = self._snapshots(24)
        screen.list_view.update(len(screen.processes))
        processes = FakeProcesses()
        for _ in range(23):
            screen.handle(DOWN, processes)
        self.assertEqual(screen.list_view.selected, 23)
        self.assertIn(23, range(screen.list_view.first, screen.list_view.last))
        self.assertTrue(screen.list_view.has_above)

    def test_back_still_exits_and_a_still_opens_help(self):
        """Preserve the original menu and help actions while scrolling."""
        screen = ProcMonitorScreen()
        processes = FakeProcesses()
        self.assertFalse(screen.handle(UP, processes))
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertTrue(screen.show_help)
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertFalse(screen.show_help)
        self.assertTrue(screen.handle(BACK, processes))


class BleedingListScrollTests(unittest.TestCase):
    """Guard device, service, and result scrolling in BLEEDING."""

    def test_device_selection_scrolls_past_the_first_page(self):
        """Select a device below the initial visible rows with DOWN."""
        devices = [{"address": f"FC:FC:48:00:00:{index:02X}", "name": f"D{index}"} for index in range(12)]
        engine = FakeEngine(devices, [])
        screen = BleedingScreen(engine)
        processes = FakeProcesses()
        screen.devices = devices
        screen.phase = "devices"
        screen.device_view.update(len(devices))
        for _ in range(11):
            screen.handle(DOWN, processes)
        self.assertEqual(screen.device_view.selected, 11)
        self.assertIn(11, range(screen.device_view.first, screen.device_view.last))
        screen.handle(OPEN, processes)
        self.assertEqual(screen.editor.value, devices[11]["address"])

    def test_services_keep_the_selected_row_visible(self):
        """Scroll the service list instead of hiding selections below row eight."""
        services = [{"name": f"S{index}", "uuid": f"uuid-{index}"} for index in range(15)]
        screen = BleedingScreen(FakeEngine([], services))
        processes = FakeProcesses()
        screen.services = services
        screen.phase = "services"
        screen.service_view.update(len(services))
        for _ in range(14):
            screen.handle(DOWN, processes)
        self.assertIn(14, range(screen.service_view.first, screen.service_view.last))
        self.assertTrue(screen.service_view.has_above)
        self.assertFalse(screen.handle(BACK, processes))
        self.assertEqual(screen.phase, "settings")

    def test_long_result_messages_are_wrapped_and_scrollable(self):
        """Show the whole validation error instead of only 34 characters."""
        message = "Falta bleak: instala el paquete en el entorno virtual"
        screen = BleedingScreen(FakeEngine([], []))
        screen.result_message = message
        processes = FakeProcesses()
        screen.phase = "result"
        lines = screen._result_lines()
        self.assertGreater(len(lines), 1)
        self.assertIn("virtual", lines[-1])
        screen.handle(DOWN, processes)
        self.assertEqual(screen.result_view.selected, 1)
        self.assertEqual(screen.handle(BACK, processes), True)

    def test_help_and_settings_keep_their_actions(self):
        """Keep A/B navigation while adding arrows for long help text."""
        screen = BleedingScreen(FakeEngine([], []))
        processes = FakeProcesses()
        screen.phase = "help"
        self.assertFalse(screen.handle(LEFT, processes))
        self.assertFalse(screen.handle(UP, processes))
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertEqual(screen.phase, "settings")
        self.assertTrue(screen.handle(BACK, processes))


if __name__ == "__main__":
    unittest.main()
