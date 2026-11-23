import logging
import tempfile
import unittest
from pathlib import Path

from core.plugins import PluginCatalog


ROOT = Path(__file__).resolve().parents[1]


class PluginCatalogTests(unittest.TestCase):
    def test_loads_all_first_party_modules(self):
        catalog = PluginCatalog(ROOT / "modules", logging.getLogger("test.plugins"))

        self.assertEqual(len(catalog.plugins), 6)
        self.assertEqual(catalog.errors, [])
        self.assertIn("network_tools", {plugin.identifier for plugin in catalog.plugins})

    def test_skips_invalid_manifest_and_reports_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            module_dir = Path(temporary) / "broken_module"
            module_dir.mkdir()
            (module_dir / "manifest.yaml").write_text("name: missing-fields\n", encoding="utf-8")
            catalog = PluginCatalog(Path(temporary), logging.getLogger("test.plugins"))

        self.assertEqual(catalog.plugins, [])
        self.assertEqual(len(catalog.errors), 1)
        self.assertIn("broken_module", catalog.errors[0])


if __name__ == "__main__":
    unittest.main()
