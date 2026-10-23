"""The owner loop is shut down at interpreter exit, so an owned bed socket is closed, not leaked.

The owner loop runs on a daemon thread for owned subscriptions. At exit, the daemon thread is
killed, and any socket still open on it is reported as a ResourceWarning. The shutdown hook must
cancel the tasks on the owner loop, let them finish (so their connections close), and stop the loop.
"""

import asyncio
import time

import pytest

from bbsengine6.startup import message_subscription as ms


@pytest.fixture
def fresh_owner(monkeypatch):
    monkeypatch.setattr(ms, "_owner_loop", None)
    yield
    loop = ms._owner_loop
    if loop is not None and not loop.is_closed():
        loop.call_soon_threadsafe(loop.stop)
    monkeypatch.setattr(ms, "_owner_loop", None)


@pytest.mark.unit
def test_shutdown_cancels_and_finishes_owned_tasks(fresh_owner):
    loop = ms.owner_loop()
    done = {}

    async def owned():
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            # Stand-in for a connection's aclose() running while the task unwinds.
            await asyncio.sleep(0.01)
            done["closed"] = True
            raise

    asyncio.run_coroutine_threadsafe(_spawn(owned), loop).result(timeout=5)
    ms.shutdown_owner_loop()
    assert done.get("closed") is True, "owned task must finish its close before shutdown returns"


async def _spawn(coro_fn):
    return asyncio.get_running_loop().create_task(coro_fn())


@pytest.mark.unit
def test_shutdown_stops_the_owner_loop_and_its_thread(fresh_owner):
    loop = ms.owner_loop()
    ms.shutdown_owner_loop()
    assert loop.is_closed()


@pytest.mark.unit
def test_shutdown_is_a_no_op_when_no_owner_loop_exists(fresh_owner):
    ms.shutdown_owner_loop()  # must not raise
    assert ms._owner_loop is None


@pytest.mark.unit
def test_shutdown_is_idempotent(fresh_owner):
    ms.owner_loop()
    ms.shutdown_owner_loop()
    ms.shutdown_owner_loop()
    assert ms._owner_loop is None


@pytest.mark.unit
def test_owner_loop_is_registered_for_exit(fresh_owner, monkeypatch):
    import atexit
    registered = []
    monkeypatch.setattr(atexit, "register", lambda fn, *a, **k: registered.append(fn))
    monkeypatch.setattr(ms, "_atexit_registered", False)
    ms.owner_loop()
    assert ms.shutdown_owner_loop in registered
