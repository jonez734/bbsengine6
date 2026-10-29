"""Read-through module state: a module's names are properties over the current interaction."""

import importlib
import sys
import types

import pytest

i = importlib.import_module("bbsengine6.interaction")


@pytest.fixture
def probe(monkeypatch):
    """A throwaway module with one per-interaction name, installed as read-through."""
    name = "bbsengine6_readthrough_probe"
    mod = types.ModuleType(name)
    mod.KEEP = "module-only"
    sys.modules[name] = mod
    # The Interaction must carry the field the probe reads through.
    monkeypatch.setattr(i.Session, "probe_value", None, raising=False)
    i.install_read_through(name, {"VALUE": "probe_value"})
    yield sys.modules[name]
    sys.modules.pop(name, None)


def test_read_returns_the_current_interaction_value(probe):
    s = i.new_session(name="a")
    s.probe_value = "from-a"
    with i.use_session(s):
        assert probe.VALUE == "from-a"


def test_write_lands_in_the_current_interaction(probe):
    s = i.new_session(name="a")
    with i.use_session(s):
        probe.VALUE = "written"
        assert s.probe_value == "written"


def test_two_interactions_do_not_share_the_value(probe):
    a = i.new_session(name="a")
    b = i.new_session(name="b")
    a.probe_value = "A"
    b.probe_value = "B"
    with i.use_session(a):
        assert probe.VALUE == "A"
    with i.use_session(b):
        assert probe.VALUE == "B"


def test_unlisted_names_stay_ordinary_module_attributes(probe):
    assert probe.KEEP == "module-only"
