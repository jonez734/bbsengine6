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
