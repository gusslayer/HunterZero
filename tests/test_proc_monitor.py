"""Verify the Process Monitor module navigation and data formatting."""

import unittest
from pathlib import Path

import yaml

from core.input import BACK, OPEN
from modules.proc_monitor.main import _format_elapsed
from modules.proc_monitor.screen import ProcMonitorScreen


class FakeProcessManager:
    """No-op process manager for screen navigation tests."""

    def __init__(self) -> None:
        """Initialize empty message, output, and running state."""
        self.message = ""
        self.output = ""
        self.running = None


class ProcMonitorTests(unittest.TestCase):
    """Exercise the manifest, help toggle, exit, and snapshot refresh."""

    def test_manifest_declares_module_metadata(self):
        """Validate id, name, description, icon, and screen of the manifest."""
        manifest_path = Path(__file__).resolve().parents[1] / "modules" / "proc_monitor" / "manifest.yaml"
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "proc_monitor")
        self.assertEqual(data["name"], "Monitor de Procesos")
        self.assertEqual(data["icon"], "activity")
        self.assertEqual(data["screen"], "screen.py")

    def test_handle_toggles_help_and_b_exits_to_menu(self):
        """Toggle the help view with A and exit to the menu with B."""
        screen = ProcMonitorScreen()
        processes = FakeProcessManager()
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertTrue(screen.show_help)
        self.assertFalse(screen.handle(OPEN, processes))
        self.assertFalse(screen.show_help)
        self.assertTrue(screen.handle(BACK, processes))

    def test_sync_refreshes_the_snapshot(self):
        """Refresh the summarized process snapshot on every app tick."""
        screen = ProcMonitorScreen()
        self.assertIsInstance(screen.processes, tuple)
        screen.sync(FakeProcessManager())
        self.assertIsInstance(screen.processes, tuple)

    def test_format_elapsed_produces_compact_strings(self):
        """Format elapsed seconds as seconds, minutes, or hours strings."""
        self.assertEqual(_format_elapsed(5), "5s")
        self.assertEqual(_format_elapsed(65), "1m 05s")
        self.assertEqual(_format_elapsed(3600), "1h 00m")


if __name__ == "__main__":
    unittest.main()
