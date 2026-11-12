"""The seam's settings are configurable: capacity, idle expiry, and the logger name.

A consumer (zoid6, through bed) sets them from its config's ``bbsengine6`` section by calling
``seam.configure``. With nothing configured, the defaults apply: 1000 events, 300 seconds, and the
logger ``bbsengine6.seam``.
"""

import pytest

from bbsengine6.seam import config as seam_config
from bbsengine6.seam import domain as dm
from bbsengine6.seam import events

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    seam_config.reset()
    yield
    seam_config.reset()


def test_defaults_when_nothing_is_configured():
    assert seam_config.get_capacity() == 1000
    assert seam_config.get_idle_seconds() == 300.0
    assert seam_config.get_logger_name() == "bbsengine6.seam"


def test_configure_sets_capacity_used_by_a_new_domain():
    seam_config.configure(capacity=5)
    d = dm.Domain("casino")
    s = d.subscribe()
    for i in range(9):
        d.emit(events.Event("info", "t1", None, {"text": str(i)}))
    got = d.read(s)
    assert got[0].kind == "lagged" and got[0].payload["missed"] == 4


def test_configure_sets_idle_seconds_used_by_expiry():
    now = [0.0]
    seam_config.configure(idle_seconds=10)
    d = dm.Domain("casino", clock=lambda: now[0])
    s = d.subscribe()
    now[0] = 11.0
    d.expire_idle()
    with pytest.raises(KeyError):
        d.read(s)


def test_configure_sets_the_logger_name(monkeypatch):
    seen = []
    monkeypatch.setattr(dm, "_log_warning", lambda msg: seen.append(msg))
    seam_config.configure(logger_name="zoid6.seam")
    assert seam_config.get_logger_name() == "zoid6.seam"


def test_configure_only_changes_given_keys():
    seam_config.configure(capacity=7)
    seam_config.configure(idle_seconds=60)
    assert seam_config.get_capacity() == 7
    assert seam_config.get_idle_seconds() == 60.0


@pytest.mark.parametrize("bad", [0, -1, "1000", 2.5, True])
def test_bad_capacity_is_rejected(bad):
    with pytest.raises(ValueError):
        seam_config.configure(capacity=bad)


@pytest.mark.parametrize("bad", [0, -5, "300", True])
def test_bad_idle_seconds_is_rejected(bad):
    with pytest.raises(ValueError):
        seam_config.configure(idle_seconds=bad)


@pytest.mark.parametrize("bad", ["", "  ", 5])
def test_bad_logger_name_is_rejected(bad):
    with pytest.raises(ValueError):
        seam_config.configure(logger_name=bad)


def test_unknown_key_is_rejected():
    with pytest.raises(ValueError):
        seam_config.configure(capacty=5)
