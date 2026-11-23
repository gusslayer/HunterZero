"""Keep explanatory documentation on every project function."""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FunctionDocstringTests(unittest.TestCase):
    """Prevent undocumented functions from entering the application."""

    def test_all_python_functions_have_docstrings(self):
        """Require a purpose docstring on every function and method."""
        source_roots = (ROOT / "core", ROOT / "modules", ROOT / "tests")
        undocumented = []
        for source_root in source_roots:
            for path in source_root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if ast.get_docstring(node) is None:
                            undocumented.append(f"{path}:{node.lineno}:{node.name}")

        self.assertEqual(undocumented, [])


if __name__ == "__main__":
    unittest.main()
