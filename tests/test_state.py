import json
import tempfile
import unittest
from pathlib import Path

from core.state import UIState


class UIStateTests(unittest.TestCase):
    def test_saves_and_clamps_selected_item(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ui_state.json"
            state = UIState(path)
            state.selected = 20
            state.save()

            restored = UIState(path)
            restored.load(4)

        self.assertEqual(restored.selected, 3)

    def test_invalid_state_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ui_state.json"
            path.write_text(json.dumps({"selected": "invalid"}), encoding="utf-8")
            state = UIState(path)

            with self.assertRaises(RuntimeError):
                state.load(3)


if __name__ == "__main__":
    unittest.main()
