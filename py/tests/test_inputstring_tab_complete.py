"""Tab completion through inputstring(), checked with the same cases as
tests/tab_complete_check.py (run that script directly for the report).
"""

import importlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
check = importlib.import_module("tab_complete_check")


@pytest.mark.parametrize("name,keys,expected,extra", check.CASES, ids=[c[0] for c in check.CASES])
def test_tab_complete_case(name, keys, expected, extra):
    assert check.run_case(keys, extra) == expected


def test_empty_double_tab_lists_all_completions(monkeypatch):
    # Tab on an empty word prints every completion; the buffer stays empty.
    inp = check.inp_mod
    printed = []
    real = inp.print_matches

    def record(matches, *a, **k):
        printed.append(list(matches))
        return real(matches, *a, **k)

    monkeypatch.setattr(inp, "print_matches", record)
    assert check.run_case([b"\t", b"\t", b"\r"], {}) == ""
    assert printed, "second Tab on an empty word must print the list"
    assert printed[-1] == check.WORDS
