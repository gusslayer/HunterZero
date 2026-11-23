"""Verify the update screen flow and its interaction with the process manager."""

import unittest

from core.input import BACK, OPEN
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

    def test_footer_hints_match_the_current_phase(self):
        """Return action hints for confirm, running, and result phases."""
        screen = UpdateScreen()
        self.assertEqual(
            screen.footer_hints(),
            [("A ACTUALIZAR", 24), ("B VOLVER", 335)],
        )
        screen.phase = "running"
        self.assertEqual(screen.footer_hints(), [("B CANCELAR", 24)])
        screen.phase = "result"
        self.assertEqual(screen.footer_hints(), [("A/B VOLVER", 24)])


if __name__ == "__main__":
    unittest.main()
