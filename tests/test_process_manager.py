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

    def test_start_update_is_rejected_when_bash_is_missing(self):
        """Refuse the update launch when bash is not on PATH."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))
            with patch("core.process_manager.shutil.which", return_value=None):
                started = manager.start_update()

        self.assertFalse(started)
        self.assertEqual(
            manager.message,
            "No está instalado bash; no se puede actualizar ahora.",
        )

    def test_update_script_is_not_a_tool_command(self):
        """Keep bash out of the tool allowlist so only the update screen uses it."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))
            self.assertFalse(manager.start_command("bash", ["bash", "-c", "echo"], 10))

        self.assertEqual(manager.message, "Comando no permitido.")

    def test_gui_update_skips_root_steps_via_environment(self):
        """Mark GUI updates so the script does not call sudo or restart the service."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))
            with patch("core.process_manager.shutil.which", return_value="/usr/bin/bash"), patch(
                "core.process_manager.subprocess.Popen"
            ) as popen:
                popen.return_value.pid = 42
                popen.return_value.poll.return_value = None
                self.assertTrue(manager.start_update())

        self.assertEqual(popen.call_args.kwargs["env"]["HUNTERZERO_UPDATE_GUI"], "1")

    def test_update_failure_mentions_installing_declared_dependencies(self):
        """Show the dependency-install hint when the update command fails."""
        with tempfile.TemporaryDirectory() as temporary:
            manager = ProcessManager(Path(temporary), logging.getLogger("test.processes"))
            with patch("core.process_manager.shutil.which", return_value="/usr/bin/bash"), patch(
                "core.process_manager.subprocess.Popen"
            ) as popen:
                popen.return_value.pid = 42
                popen.return_value.poll.return_value = 1
                self.assertTrue(manager.start_update())
                manager.update()

        self.assertIn("terminó con error (1)", manager.message)
        self.assertIn("sudo bash deploy/deps.sh", manager.message)


if __name__ == "__main__":
    unittest.main()
