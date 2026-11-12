"""bbsengine6.io's timing and size settings come from a config block, with the current values as defaults.

A host calls ``io.settings.configure(section)`` with the ``io`` object of its config. Missing keys keep
the defaults; a bad value raises ValueError before anything changes. Settings are read when they are
used, so a value configured after import still takes effect.
"""

import pytest

from bbsengine6.io import settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    settings.reset()
    yield
    settings.reset()


def test_defaults_match_the_previous_constants():
    assert settings.get("query_settle_seconds") == 0.25
    assert settings.get("esc_tail_wait_seconds") == 0.05
    assert settings.get("inputstring_getch_timeout_seconds") == 0.015
    assert settings.get("inputstring_history_size") == 500
    assert settings.get("inputstring_pagesize") == 10
    assert settings.get("paste_max_bytes") == 65536


def test_configure_none_or_empty_keeps_defaults():
    settings.configure(None)
    settings.configure({})
    assert settings.get("inputstring_history_size") == 500


def test_configured_value_is_used_when_read():
    settings.configure({"inputstring_history_size": 50})
    assert settings.get("inputstring_history_size") == 50


def test_only_given_keys_change():
    settings.configure({"paste_max_bytes": 1024})
    assert settings.get("paste_max_bytes") == 1024
    assert settings.get("inputstring_pagesize") == 10


def test_unknown_key_is_rejected_and_nothing_changes():
    with pytest.raises(ValueError):
        settings.configure({"paste_max_bytes": 1024, "not_a_setting": 1})
    assert settings.get("paste_max_bytes") == 65536


@pytest.mark.parametrize("key", ["query_settle_seconds", "esc_tail_wait_seconds",
                                 "inputstring_getch_timeout_seconds"])
@pytest.mark.parametrize("bad", [0, -0.1, "0.2", True])
def test_bad_timing_is_rejected(key, bad):
    with pytest.raises(ValueError):
        settings.configure({key: bad})


@pytest.mark.parametrize("key", ["inputstring_history_size", "inputstring_pagesize", "paste_max_bytes"])
@pytest.mark.parametrize("bad", [0, -3, 2.5, "10", True])
def test_bad_size_is_rejected(key, bad):
    with pytest.raises(ValueError):
        settings.configure({key: bad})


def test_comment_keys_are_ignored():
    settings.configure({"_comment": "note", "inputstring_pagesize": 4})
    assert settings.get("inputstring_pagesize") == 4
