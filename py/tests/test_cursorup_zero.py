"""{cursorup:0} is not a defined move: the count 0 is sent as ESC[0A, which terminals read as one row, while the engine
tracks no movement. Drawing code must use an absolute {curpos} when it needs a row, not a zero-count cursor up."""

import importlib
import unittest

E = importlib.import_module("bbsengine6.io.echo")


class TestCursorUpCount(unittest.TestCase):
    def test_a_count_of_one_moves_one_row_in_the_model(self):
        tok = E.Token(kind="CUU", repeat=1, text="{cursorup:1}", args=("1",))
        out = list(E._handle_cuu(tok))[0]
        self.assertEqual(out.track, {"drow": -1})

    def test_no_drawing_code_sends_a_zero_count_cursor_up(self):
        import pathlib
        src = pathlib.Path(E.__file__).parents[1] / "util.py"
        self.assertNotIn("{cursorup:0}", src.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
