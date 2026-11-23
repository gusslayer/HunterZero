import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.process_manager import ProcessManager


class ProcessManagerTests(unittest.TestCase):
    """Verify command allowlisting, argv handling, and timeout constraints."""

    def test_only_allowlisted_command_starts_without_a_shell(self):
        """Start the allowlisted executable with shell disabled."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))
            with patch("core.process_manager.shutil.which", return_value="/usr/bin/ping"), patch(
                "core.process_manager.subprocess.Popen"
            ) as popen:
                popen.return_value.pid = 42
                popen.return_value.poll.return_value = None

                started = manager.start_command("ping privado", ["ping", "-c", "2"], 10)

        self.assertTrue(started)
        self.assertIsNotNone(manager.running)
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertEqual(
            popen.call_args.args[0],
            ["/usr/bin/ping", "-c", "2"],
        )

    def test_arbitrary_commands_and_unbounded_timeout_are_rejected(self):
        """Reject shells, arbitrary executables, and unbounded timeouts."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))

            self.assertFalse(manager.start_command("shell", ["sh", "-c", "echo bad"], 10))
            self.assertFalse(manager.start_command("ping", ["ping"], 10_000))

        self.assertEqual(manager.message, "Tiempo límite fuera del rango permitido.")


if __name__ == "__main__":
    unittest.main()
