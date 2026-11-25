"""Verify the update screen flow and its interaction with the process manager."""

import unittest

import pygame

from core import theme
from core.input import BACK, DOWN, OPEN, UP
from core.ui.update_screen import UpdateScreen


class FakeProcessManager:
    """Capture the update launch without starting a real process."""

    def __init__(self, started: bool = True):
        """Initialize fake state, including an active process marker."""
        self.message = ""
        self.output = ""
        self.running = object() if started else None
        self.started = False
        self.stopped = False

    def start_update(self) -> bool:
        """Record the update launch and report success."""
        self.started = True
        return True

    def stop(self):
        """Simulate cancellation of the active update process."""
        self.stopped = True
        self.running = None
        self.message = "Cancelado"


class UpdateScreenTests(unittest.TestCase):
    """Exercise the confirm, running, and result phases of the update screen."""

    def test_a_starts_the_update_and_result_exits_to_menu(self):
        """Confirm with A, run until the process finishes, and exit with A."""
        screen = UpdateScreen()
        processes = FakeProcessManager()
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertTrue(processes.started)
        self.assertEqual(screen.phase, "running")

        processes.running = None
        screen.sync(processes)
        self.assertEqual(screen.phase, "result")
        self.assertTrue(screen.handle(OPEN, processes))

    def test_b_from_the_confirm_phase_exits_the_menu(self):
        """B from the confirmation returns to the menu without launching."""
        screen = UpdateScreen()
        processes = FakeProcessManager()
        self.assertTrue(screen.handle(BACK, processes))
        self.assertFalse(processes.started)

    def test_running_phase_renders_live_output(self):
        """Draw elapsed time and captured output without leaving the running phase."""
        screen = UpdateScreen()
        screen.phase = "running"
        screen.started_at = 1.0
        processes = FakeProcessManager()
        processes.output = "Recibiendo objetos..."
        pygame.font.init()
        surface = pygame.Surface((320, 240))
        screen.draw(
            surface,
            theme.load_font(16),
            theme.load_font(8),
            theme.load_font(8),
            processes,
            None,
        )
        self.assertEqual(screen.phase, "running")

    def test_b_during_the_update_cancels_the_process(self):
        """B during the running phase cancels the update process."""
        screen = UpdateScreen()
        screen.phase = "running"
        processes = FakeProcessManager()
        self.assertFalse(screen.handle(BACK, processes))
        self.assertTrue(processes.stopped)

    def test_a_failed_update_shows_the_message_in_the_result_phase(self):
        """A blocked update launch moves to the result phase with a message."""

        class FailingProcessManager(FakeProcessManager):
            """Report a blocked update launch."""

            def start_update(self) -> bool:
                """Simulate a blocked update and record the message."""
                self.started = True
                self.message = "Ya hay una herramienta en ejecución."
                return False

        screen = UpdateScreen()
        processes = FailingProcessManager()
        screen.handle(OPEN, processes)
        self.assertEqual(screen.phase, "result")
        self.assertEqual(processes.message, "Ya hay una herramienta en ejecución.")

    def test_long_update_output_can_be_scrolled(self):
        """Scroll the complete git log instead of showing only its last lines."""
        screen = UpdateScreen()
        screen.phase = "result"
        processes = FakeProcessManager(started=False)
        processes.output = "\n".join(f"linea {index}" for index in range(30))
        self.assertGreater(len(screen._result_lines(processes)), 10)
        self.assertFalse(screen.handle(DOWN, processes))
        self.assertEqual(screen.result_view.selected, 1)
        self.assertFalse(screen.handle(UP, processes))
        self.assertEqual(screen.result_view.selected, 0)
        self.assertTrue(screen.handle(OPEN, processes))

    def test_footer_hints_match_the_current_phase(self):
        """Return action hints for confirm, running, and result phases."""
        screen = UpdateScreen()
        self.assertEqual(
            screen.footer_hints(),
            [("A ACTUALIZAR", 12), ("B VOLVER", 168)],
        )
        screen.phase = "running"
        self.assertEqual(screen.footer_hints(), [("B CANCELAR", 12)])
        screen.phase = "result"
        self.assertEqual(screen.footer_hints(), [("ARR/ABA TEXTO", 8), ("A/B VOLVER", 150)])


if __name__ == "__main__":
    unittest.main()
