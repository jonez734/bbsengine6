"""
Direct tests for bbsengine6.startup.message_subscription.

Covers the no-moniker early return, the missing-config early
return, the bed-package ImportError fallback, and the sync
wrapper's asyncio.run dispatch.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


def _load():
    return importlib.import_module("bbsengine6.startup.message_subscription")


def _make_fake_bed_module(*, messageservice_get_message_client):
    """Build a fake ``bed`` package tree and return the dict to pass
    to ``patch.dict(sys.modules, ...)`` so that
    ``from bed.client.messageservice import get_message_client``
    resolves to the supplied callable.

    Returns a dict like:
        {
            "bed": <module>,
            "bed.client": <module>,
            "bed.client.connection": <module>,
            "bed.client.messageservice": <module>,
        }
    where the messageservice module exposes ``get_message_client``
    bound to the supplied callable.
    """
    from types import ModuleType, SimpleNamespace

    bed = ModuleType("bed")
    bed_client = ModuleType("bed.client")
    bed_connection = ModuleType("bed.client.connection")
    bed_messageservice = ModuleType("bed.client.messageservice")

    bed.client = bed_client
    bed_client.connection = bed_connection
    bed_client.messageservice = bed_messageservice
    bed_messageservice.get_message_client = messageservice_get_message_client

    return {
        "bed": bed,
        "bed.client": bed_client,
        "bed.client.connection": bed_connection,
        "bed.client.messageservice": bed_messageservice,
    }


def _make_args(bed_host=None, bed_port=None) -> argparse.Namespace:
    return argparse.Namespace(
        databasename="zoid6",
        bed_host=bed_host,
        bed_port=bed_port,
    )


# ---------------------------------------------------------------------------
# _connect_bed
# ---------------------------------------------------------------------------


class TestConnectBed:
    def test_returns_none_when_bed_host_missing(self):
        ms = _load()
        # bed_host is None, so the function returns None BEFORE
        # the `from bed.client...` import on line 32.
        result = asyncio.run(ms._connect_bed(_make_args(bed_port=8765)))
        assert result is None

    def test_returns_none_when_bed_port_missing(self):
        ms = _load()
        # Same as above, but for bed_port.
        result = asyncio.run(ms._connect_bed(_make_args(bed_host="localhost")))
        assert result is None

    def test_returns_none_when_bed_package_not_installed(self):
        ms = _load()
        # Block the `from bed.client.connection import BedConnection` import
        with patch.dict(sys.modules, {"bed": None, "bed.client": None, "bed.client.connection": None}):
            with patch("bbsengine6.io.echo_traceback") as trace:
                result = asyncio.run(ms._connect_bed(_make_args("localhost", 8765)))
        assert result is None
        assert trace.call_count == 1

    def test_returns_connection_when_bed_available(self):
        ms = _load()
        fake_conn = MagicMock()

        # Build a fake bed.client.connection module with BedConnection
        fake_bed = MagicMock()
        fake_bed.BedConnection = MagicMock(return_value=fake_conn)

        with patch.dict(
            sys.modules,
            {
                "bed": MagicMock(),
                "bed.client": MagicMock(),
                "bed.client.connection": fake_bed,
            },
        ):
            result = asyncio.run(ms._connect_bed(_make_args("localhost", 8765)))

        assert result is fake_conn
        fake_bed.BedConnection.assert_called_once()


# ---------------------------------------------------------------------------
# subscribe_to_bed
# ---------------------------------------------------------------------------


class TestSubscribeToBed:
    def test_returns_false_when_moniker_empty(self):
        ms = _load()
        result = asyncio.run(ms.subscribe_to_bed(_make_args(), ""))
        assert result is False

    def test_returns_false_when_moniker_none(self):
        ms = _load()
        result = asyncio.run(ms.subscribe_to_bed(_make_args(), None))
        assert result is False

    def test_returns_false_when_connect_bed_returns_none(self):
        ms = _load()
        with patch.object(ms, "_connect_bed", return_value=None):
            result = asyncio.run(ms.subscribe_to_bed(_make_args(), "alice"))
        assert result is False

    def test_returns_true_when_bed_replies_ok(self):
        ms = _load()
        fake_conn = MagicMock()
        fake_client = MagicMock()

        async def _fake_subscribe(moniker):
            return {"ok": True}

        fake_client.subscribe = _fake_subscribe

        # Inject a fake `bed.client.messageservice` module into
        # sys.modules so the `from bed.client.messageservice import
        # get_message_client` inside subscribe_to_bed resolves.
        fake_bed = _make_fake_bed_module(
            messageservice_get_message_client=lambda conn: fake_client
        )

        with patch.object(ms, "_connect_bed", return_value=fake_conn), \
             patch.dict(sys.modules, fake_bed):
            result = asyncio.run(ms.subscribe_to_bed(_make_args(), "alice"))

        assert result is True

    def test_returns_false_when_bed_replies_not_ok(self):
        ms = _load()
        fake_conn = MagicMock()
        fake_client = MagicMock()

        async def _fake_subscribe(moniker):
            return {"ok": False, "error": "nope"}

        fake_client.subscribe = _fake_subscribe

        fake_bed = _make_fake_bed_module(
            messageservice_get_message_client=lambda conn: fake_client
        )

        with patch.object(ms, "_connect_bed", return_value=fake_conn), \
             patch.dict(sys.modules, fake_bed):
            result = asyncio.run(ms.subscribe_to_bed(_make_args(), "alice"))

        assert result is False

    def test_swallows_exception_and_returns_false(self):
        """An exception in subscribe() itself is caught and turned
        into False. The inner try/except at message_subscription.py
        lines 60-62 wraps the whole get_message_client + subscribe
        block."""
        ms = _load()
        fake_conn = MagicMock()
        fake_client = MagicMock()

        async def _explode(moniker):
            raise RuntimeError("boom")

        fake_client.subscribe = _explode

        fake_bed = _make_fake_bed_module(
            messageservice_get_message_client=lambda c: fake_client
        )

        with patch.object(ms, "_connect_bed", return_value=fake_conn), \
             patch.dict(sys.modules, fake_bed), \
             patch("bbsengine6.io.echo_traceback") as trace:
            result = asyncio.run(ms.subscribe_to_bed(_make_args(), "alice"))
        assert result is False
        assert trace.call_count == 1

    def test_swallows_exception_from_get_message_client(self):
        ms = _load()
        fake_conn = MagicMock()

        def _explode(conn):
            raise RuntimeError("client exploded")

        fake_bed = _make_fake_bed_module(
            messageservice_get_message_client=_explode
        )

        with patch.object(ms, "_connect_bed", return_value=fake_conn), \
             patch.dict(sys.modules, fake_bed), \
             patch("bbsengine6.io.echo_traceback") as trace:
            result = asyncio.run(ms.subscribe_to_bed(_make_args(), "alice"))
        assert result is False
        assert trace.call_count == 1


# ---------------------------------------------------------------------------
# subscribe_to_bed_sync
# ---------------------------------------------------------------------------


class TestSubscribeToBedSync:
    def test_returns_false_when_moniker_empty(self):
        ms = _load()
        with patch.object(ms, "asyncio") as _asyncio:
            result = ms.subscribe_to_bed_sync(_make_args(), "")
        # No asyncio.run should be called for empty moniker
        assert not _asyncio.run.called
        assert result is False

    def test_delegates_to_asyncio_run(self):
        ms = _load()
        coro_holder = []

        def _capture_run(coro, *args, **kwargs):
            coro_holder.append(coro)
            return True

        with patch.object(ms, "asyncio") as _asyncio:
            _asyncio.run.side_effect = _capture_run
            result = ms.subscribe_to_bed_sync(_make_args(), "alice")

        _asyncio.run.assert_called_once()
        assert result is True
        # The coroutine passed to asyncio.run is subscribe_to_bed(args, "alice").
        # Drive it to completion to suppress the "coroutine was never
        # awaited" warning during garbage collection.
        if coro_holder:
            asyncio.run(coro_holder[0])

    def test_swallows_exception_from_asyncio_run(self):
        ms = _load()
        coro_holder = []

        def _explode(coro, *args, **kwargs):
            coro_holder.append(coro)
            raise RuntimeError("loop crashed")

        with patch.object(
            ms, "asyncio"
        ) as _asyncio, patch("bbsengine6.io.echo_traceback") as trace:
            _asyncio.run.side_effect = _explode
            result = ms.subscribe_to_bed_sync(_make_args(), "alice")

        assert result is False
        assert trace.call_count == 1
        # Drive the captured coroutine to completion to avoid
        # "coroutine was never awaited" warnings during GC.
        if coro_holder:
            try:
                asyncio.run(coro_holder[0])
            except Exception:
                pass
