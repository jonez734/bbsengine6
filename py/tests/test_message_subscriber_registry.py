"""bbsengine6 reaches bed's push subscription through a registry, not imports.

bbsengine6 must not import bed. bed registers its subscriber at startup.
With no subscriber registered, subscription returns False and the session
falls back to DB polling.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import bbsengine6.startup.message_subscription as ms


def test_module_has_no_bed_imports():
    src = Path(ms.__file__).read_text()
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "bed":
            offenders.append(f"from {node.module}")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "bed":
                    offenders.append(f"import {a.name}")
    assert offenders == [], f"bbsengine6 must not import bed: {offenders}"


def test_set_and_get_subscriber_roundtrip():
    prev = ms.get_subscriber()
    try:
        fn = MagicMock(name="subscriber")
        ms.set_subscriber(fn)
        assert ms.get_subscriber() is fn
    finally:
        ms.set_subscriber(prev)


def test_no_subscriber_returns_false():
    prev = ms.get_subscriber()
    try:
        ms.set_subscriber(None)
        result = asyncio.run(ms.subscribe_to_bed(MagicMock(debug=False), "jam"))
        assert result is False
    finally:
        ms.set_subscriber(prev)


def test_registered_subscriber_is_called_with_moniker():
    prev = ms.get_subscriber()

    async def fake(args, moniker, **kwargs):
        return True

    calls = []

    async def recording(args, moniker, **kwargs):
        calls.append((moniker, kwargs))
        return True

    try:
        ms.set_subscriber(recording)
        result = asyncio.run(ms.subscribe_to_bed(MagicMock(debug=False), "jam", bed="H"))
        assert result is True
        assert calls == [("jam", {"bed": "H"})]
    finally:
        ms.set_subscriber(prev)


def test_empty_moniker_still_returns_false_without_subscriber_call():
    prev = ms.get_subscriber()
    called = []

    async def recording(args, moniker, **kwargs):
        called.append(moniker)
        return True

    try:
        ms.set_subscriber(recording)
        assert asyncio.run(ms.subscribe_to_bed(MagicMock(debug=False), "  ")) is False
        assert called == []
    finally:
        ms.set_subscriber(prev)
