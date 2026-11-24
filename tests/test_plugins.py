import logging
import tempfile
import unittest
from pathlib import Path

from core.plugins import PluginCatalog


ROOT = Path(__file__).resolve().parents[1]


class PluginCatalogTests(unittest.TestCase):
    """Verify implemented-module discovery and manifest validation."""

    def test_loads_only_modules_with_implemented_screens(self):
        """Discover the five real modules and reject former placeholders."""
        catalog = PluginCatalog(ROOT / "modules", logging.getLogger("test.plugins"))

        self.assertEqual(len(catalog.plugins), 5)
        self.assertEqual(catalog.errors, [])
        identifiers = {plugin.identifier for plugin in catalog.plugins}
        self.assertEqual(
            identifiers,
            {"ping", "nmap", "nslookup", "system_monitor", "proc_monitor"},
        )
        self.assertTrue(all(plugin.screen_path.is_file() for plugin in catalog.plugins))

    def test_skips_invalid_manifest_and_reports_error(self):
        """Skip an invalid module and retain an actionable catalog error."""
        with tempfile.TemporaryDirectory() as temporary:
            module_dir = Path(temporary) / "broken_module"
            module_dir.mkdir()
            (module_dir / "manifest.yaml").write_text("name: missing-fields\n", encoding="utf-8")
            catalog = PluginCatalog(Path(temporary), logging.getLogger("test.plugins"))

        self.assertEqual(catalog.plugins, [])
        self.assertEqual(len(catalog.errors), 1)
        self.assertIn("broken_module", catalog.errors[0])

    def test_skips_a_module_without_its_screen_file(self):
        """Do not list modules that have a manifest but no implemented screen."""
        with tempfile.TemporaryDirectory() as temporary:
            module_dir = Path(temporary) / "empty_module"
            module_dir.mkdir()
            (module_dir / "manifest.yaml").write_text(
                "id: empty_module\n"
                "name: Empty\n"
                "description: No screen\n"
                "icon: system\n"
                "screen: screen.py\n",
                encoding="utf-8",
            )
            catalog = PluginCatalog(Path(temporary), logging.getLogger("test.plugins"))

        self.assertEqual(catalog.plugins, [])
        self.assertEqual(len(catalog.errors), 1)
        self.assertIn("screen.py", catalog.errors[0])


if __name__ == "__main__":
    unittest.main()
