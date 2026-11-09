"""The "is in sys.modules. reloading" debug line prints only when debug is really on.

A program that declares --debug without action="store_true" passes a string, so a value of
"False" or "0" must not turn debug on.
"""

import importlib
import sys
import types
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

module = importlib.import_module("bbsengine6.module")


@pytest.mark.parametrize("value", [True, 1, "1", "true", "yes", "on"])
def test_debug_on_values_enable_the_gate(value):
    assert module._debug_enabled(value) is True


@pytest.mark.parametrize("value", [False, 0, None, "", "False", "0", "no", "off", "anything"])
def test_other_values_leave_debug_off(value):
    assert module._debug_enabled(value) is False


def test_reload_message_is_printed_only_when_debug_is_on():
    name = "os.path"
    sys.modules.setdefault(name, importlib.import_module(name))
    for value, expected in [(True, 1), ("False", 0), (False, 0)]:
        args = types.SimpleNamespace(debug=value)
        with patch.object(module.io, "echo") as echo:
            module.load(args, name)
        msgs = [c.args[0] for c in echo.call_args_list if "reloading" in str(c.args[0])]
        assert len(msgs) == expected, (value, msgs)
