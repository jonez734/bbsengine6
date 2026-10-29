"""inputstring() on a real pty, judged on the emulated screen.

These cover the editing paths the TODO listed as untested: INSERT/overwrite with the mode
indicator, Ctrl+W (cut previous word) and Ctrl+Y (yank), and bracketed paste. Each test runs
the real prompt in a child process and reads what a terminal would show.

Requires pexpect and pyte (dev dependencies). Skipped if either is missing.
"""

import pytest

pytest.importorskip("pexpect")
pytest.importorskip("pyte")

from _pty_screen import Screen, make_prompt_program  # noqa: E402

PROMPT = "name: "


@pytest.fixture
def prompt():
    s = Screen(make_prompt_program(PROMPT))
    assert s.wait_for("name:"), s.text()
    yield s
    s.close()


def _line(s: Screen) -> str:
    row = s.find(PROMPT)
    assert row is not None, s.text()
    return s.row(row)


def _finish(s: Screen) -> str:
    s.key("\r", pause=0.3)
    assert s.wait_for("RESULT"), s.text()
    s.wait_exit()
    return s.result()


# ---- INSERT / overwrite ------------------------------------------------

def test_insert_mode_is_the_default_and_shows_no_ovr(prompt):
    prompt.type("ab", pause=0.2)
    assert not any("OVR" in r for r in prompt.rows_text()), prompt.text()


def test_insert_key_switches_to_overwrite_and_shows_ovr(prompt):
    prompt.type("abcd", pause=0.2)
    prompt.key("\x1b[2~", pause=0.3)
    assert any("OVR" in r for r in prompt.rows_text()), prompt.text()


def test_overwrite_replaces_the_character_under_the_cursor(prompt):
    prompt.type("abcd", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)  # cursor on 'c'
    prompt.key("\x1b[2~", pause=0.3)  # overwrite mode
    prompt.type("X", pause=0.3)
    assert _line(prompt) == "name: abXd", prompt.text()


def test_insert_toggled_back_inserts_again(prompt):
    prompt.type("abcd", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)
    prompt.key("\x1b[2~", pause=0.3)  # overwrite
    prompt.key("\x1b[2~", pause=0.3)  # back to insert
    prompt.type("Y", pause=0.3)
    assert _line(prompt) == "name: abYcd", prompt.text()


def test_result_after_overwrite_matches_the_screen(prompt):
    prompt.type("abcd", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)
    prompt.key("\x1b[D", pause=0.2)
    prompt.key("\x1b[2~", pause=0.3)
    prompt.type("X", pause=0.3)
    assert _finish(prompt) == "'abXd'"


# ---- Ctrl+W and Ctrl+Y -------------------------------------------------

def test_ctrl_w_cuts_the_previous_word(prompt):
    prompt.type("one two", pause=0.2)
    prompt.key("\x17", pause=0.3)  # Ctrl+W removes "two" and the space before it
    # The screen model drops trailing spaces, so the expected value has none.
    assert _line(prompt) == "name: one", prompt.text()


def test_ctrl_y_yanks_what_ctrl_w_cut(prompt):
    prompt.type("one two", pause=0.2)
    prompt.key("\x17", pause=0.3)  # cut "two"
    prompt.key("\x19", pause=0.3)  # yank it back at the cursor
    assert _line(prompt) == "name: one two", prompt.text()


def test_ctrl_y_with_nothing_cut_inserts_nothing(prompt):
    prompt.type("abc", pause=0.2)
    prompt.key("\x19", pause=0.3)
    assert _line(prompt) == "name: abc", prompt.text()


def test_ctrl_w_then_ctrl_y_result(prompt):
    prompt.type("alpha beta", pause=0.2)
    prompt.key("\x17", pause=0.3)
    prompt.key("\x19", pause=0.3)
    assert _finish(prompt) == "'alpha beta'"


# ---- bracketed paste ---------------------------------------------------

def test_bracketed_paste_inserts_the_whole_text(prompt):
    prompt.type("\x1b[200~hello world\x1b[201~", pause=0.5)
    assert _line(prompt) == "name: hello world", prompt.text()


def test_bracketed_paste_then_typing_continues_at_the_end(prompt):
    prompt.type("\x1b[200~hello\x1b[201~", pause=0.4)
    prompt.type("!", pause=0.3)
    assert _line(prompt) == "name: hello!", prompt.text()


def test_bracketed_paste_result_is_exact(prompt):
    prompt.type("\x1b[200~one two three\x1b[201~", pause=0.5)
    assert _finish(prompt) == "'one two three'"


def test_paste_with_newline_stops_at_the_line_end(prompt):
    # A newline in a paste ends the input (Enter). Text after it is not part of the value.
    prompt.type("\x1b[200~first\nsecond\x1b[201~", pause=0.5)
    assert _finish(prompt) == "'first'"
