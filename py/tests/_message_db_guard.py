"""Stop message unit tests from opening a real database connection.

Several message tests expect mocks but reach the live database through the
DAL, which writes to it. This guard makes any real connection attempt fail
loudly, so unit tests can never change a live database by accident.

Tests that need a database must request the ``db_connection`` or ``pool``
fixture from conftest; they are exempt from this guard.
"""

from __future__ import annotations

import pytest


class RealDatabaseAccessed(AssertionError):
    """A unit test tried to open a real database connection."""


def _refuse(*args, **kwargs):
    raise RealDatabaseAccessed(
        "unit test opened a real database connection; mock the DAL or mark "
        "the test as integration and request the db_connection fixture"
    )


@pytest.fixture(autouse=True)
def _no_real_database(request, monkeypatch, _message_dal_request):
    if request.node.get_closest_marker("unit") is None:
        yield
        return
    yield from _unit_guard(request, monkeypatch)


@pytest.fixture
def _message_dal_request(request):
    """Make the DAL stubs active only for unit-marked message tests."""
    if request.node.get_closest_marker("unit") is not None and "test_message" in request.node.module.__name__:
        return request.getfixturevalue("message_dal_stubs")
    return None


def _unit_guard(request, monkeypatch):
    """Refuse real connections for unit tests."""
    if "db_connection" in request.fixturenames or "pool" in request.fixturenames:
        yield
        return
    if request.node.get_closest_marker("integration") is not None:
        yield
        return
    import psycopg
    import psycopg_pool

    monkeypatch.setattr(psycopg, "connect", _refuse)
    monkeypatch.setattr(psycopg_pool.ConnectionPool, "__init__", _refuse)
    yield


# ---------------------------------------------------------------------------
# In-memory DAL boundary for message unit tests.
#
# The message service reaches the database only through these DAL modules.
# Replacing their public functions for each unit test means a test that
# forgets to mock a DAL call gets a neutral in-memory answer instead of a live
# query. Tests that need specific values still patch them explicitly; their
# patches apply after this fixture and take precedence.
# ---------------------------------------------------------------------------

import importlib
import types as _types

_DAL_MODULES = (
    "bbsengine6.message.dal.blocking",
    "bbsengine6.message.dal.messages",
    "bbsengine6.message.dal.types",
    "bbsengine6.message.dal.ratelimit",
    "bbsengine6.message.dal.recipients",
    "bbsengine6.message.dal.groups",
)


def _empty_for(annotation):
    """The value the real DAL returns for an empty table, from its annotation."""
    text = str(annotation)
    if text.startswith(("typing.Tuple", "tuple", "Tuple")):
        # Tuple annotations: a tuple of the element defaults, not one of them.
        inner = text[text.find("[") + 1:text.rfind("]")] if "[" in text else ""
        parts = [part.strip() for part in inner.split(",") if part.strip()]
        return tuple(_empty_for(part) for part in parts)
    if "List" in text or "list" in text:
        return []
    if "Dict" in text or "dict" in text:
        return {}
    if "bool" in text:
        return False
    if "int" in text:
        return 0
    if "Set" in text or "set" in text:
        return set()
    return None


def _make_stub(func):
    """A recording stub: records every call and returns the typed empty value.

    Tests assert on ``stub.call_args`` / ``assert_called_once_with`` to check
    the DAL-level behavior of the code under test.
    """
    from unittest.mock import MagicMock

    empty = _empty_for(getattr(func, "__annotations__", {}).get("return"))
    stub = MagicMock(name=func.__name__)
    # Default to a fresh empty container per call. Setting side_effect here
    # would override return_value, so a test's explicit return_value would be
    # ignored; instead use return_value for scalars and a fresh copy otherwise.
    if isinstance(empty, (list, dict, set)):
        stub.return_value = type(empty)()
    else:
        stub.return_value = empty
    return stub


def _public_functions(module):
    return [
        name for name, obj in vars(module).items()
        if not name.startswith("_") and callable(obj) and getattr(obj, "__module__", "") == module.__name__
    ]


@pytest.fixture
def message_dal_stubs(monkeypatch):
    """Replace every public message DAL function with a neutral in-memory stub."""
    stubs = {}
    for dotted in _DAL_MODULES:
        mod = importlib.import_module(dotted)
        for name in _public_functions(mod):
            stub = _make_stub(getattr(mod, name))
            monkeypatch.setattr(mod, name, stub)
            stubs[(dotted, name)] = stub
    yield stubs


@pytest.fixture(autouse=True)
def _message_enabled_restored():
    """Every message unit test starts and ends with the message system enabled.

    Some tests call disable() and re-enable() without try/finally; a failure in
    between leaked the disabled flag into later tests.
    """
    from bbsengine6.message import service

    before = service._message_enabled
    service._message_enabled = True
    yield
    service._message_enabled = before
