"""bottombar.shutdown(): echo-only restore that runs only after init(), once per init()."""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar


@pytest.fixture(autouse=True)
def _reset_flag():
    bottombar._initialized = False
    yield
    bottombar._initialized = False


def _tty():
    return patch.object(bottombar.sys.stdin, "isatty", return_value=True), \
           patch.object(bottombar.sys.stdout, "isatty", return_value=True)


@pytest.mark.unit
def test_shutdown_before_init_emits_nothing():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo") as echo:
        bottombar.shutdown()
    echo.assert_not_called()


@pytest.mark.unit
def test_init_then_shutdown_emits_clear_reset_restore_in_order_and_clears_flag():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo") as echo, patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar.init()
        echo.reset_mock()
        bottombar.shutdown()
    calls = [c.args[0] for c in echo.call_args_list]
    assert calls == ["{savecursor}{curpos:24,0}{el}", "{reset}", "{restorecursor}"]
    assert bottombar.is_initialized() is False


@pytest.mark.unit
def test_init_twice_runs_once():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo") as echo, patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar.init()
        n = echo.call_count
        bottombar.init()
    assert echo.call_count == n


@pytest.mark.unit
def test_init_after_shutdown_runs_again():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo") as echo, patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar.init()
        bottombar.shutdown()
        n = echo.call_count
        bottombar.init()
    assert echo.call_count > n


@pytest.mark.unit
def test_is_initialized_tracks_init_and_shutdown():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo"), patch.object(bottombar.terminal, "lines", return_value=24):
        assert bottombar.is_initialized() is False
        bottombar.init()
        assert bottombar.is_initialized() is True
        bottombar.shutdown()
        assert bottombar.is_initialized() is False


@pytest.mark.unit
def test_shutdown_never_raises():
    a, b = _tty()
    with a, b, patch.object(bottombar, "echo", side_effect=OSError("closed")), \
         patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar._initialized = True
        bottombar.shutdown()
    assert bottombar.is_initialized() is False
