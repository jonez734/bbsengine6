"""
Tests for bbsengine6.channel.api.handler._resolve_channel_config and the
dual-shape config read (bed.json flat vs zoid6.json nested).
"""

from __future__ import annotations

from bbsengine6.channel.api.handler import (
    _ensure_daemon_member,
    _resolve_channel_config,
)


class TestResolveChannelConfig:
    """Both flat and nested config shapes resolve correctly."""

    def test_flat_shape(self):
        config = {"channel": {"enabled": True, "auto_seed": []}}
        result = _resolve_channel_config(config)
        assert result == {"enabled": True, "auto_seed": []}

    def test_nested_shape(self):
        config = {"services": {"channel": {"enabled": True, "admin_handler": {}}}}
        result = _resolve_channel_config(config)
        assert result == {"enabled": True, "admin_handler": {}}

    def test_prefers_flat_when_both_present(self):
        config = {
            "channel": {"enabled": True, "source": "flat"},
            "services": {"channel": {"enabled": False, "source": "nested"}},
        }
        result = _resolve_channel_config(config)
        assert result["source"] == "flat"
        assert result["enabled"] is True

    def test_returns_empty_when_no_channel_section(self):
        assert _resolve_channel_config({}) == {}
        assert _resolve_channel_config({"services": {}}) == {}

    def test_returns_empty_when_section_is_not_dict(self):
        assert _resolve_channel_config({"channel": "not a dict"}) == {}
        assert _resolve_channel_config({"services": {"channel": 42}}) == {}

    def test_returns_empty_when_config_is_none(self):
        assert _resolve_channel_config(None) == {}

    def test_returns_empty_when_config_is_not_dict(self):
        assert _resolve_channel_config("string") == {}
        assert _resolve_channel_config(42) == {}


class TestEnsureDaemonMember:
    """Flat creators warn-and-skip; namespaced creators attempt insert."""

    def test_flat_creator_returns_none(self):
        # No real DB; we just check the warn-and-skip path on the
        # non-namespaced branch.
        import argparse

        args = argparse.Namespace()
        result = _ensure_daemon_member(args, "alice")
        assert result is None

    def test_empty_string_creator_returns_none(self):
        import argparse

        args = argparse.Namespace()
        result = _ensure_daemon_member(args, "")
        assert result is None

    def test_namespaced_creator_skips_shape_validation(self, monkeypatch):
        """The bypass path passes _skip_shape_validation=True to insert.

        We can't run a real insert without a DB, so we monkeypatch
        ``member.lib.insert`` to capture the kwargs and verify the
        shape-validation bypass flag is set.
        """
        import argparse
        from bbsengine6.member import lib as member_lib

        args = argparse.Namespace()

        captured_kwargs = {}

        def fake_insert(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return "moniker:casino"

        monkeypatch.setattr(member_lib, "insert", fake_insert)
        monkeypatch.setattr(member_lib, "database", type("M", (), {
            "getpool": staticmethod(lambda args: None),
            "connect": staticmethod(lambda args, pool=None: _NullCtx()),
        })())

        result = _ensure_daemon_member(args, "moniker:casino")

        assert result == "moniker:casino"
        assert captured_kwargs.get("_skip_shape_validation") is True

    def test_namespaced_creator_handles_insert_failure(self, monkeypatch):
        """When insert fails, _ensure_daemon_member returns None (warn-and-skip)."""
        import argparse
        from bbsengine6.member import lib as member_lib

        args = argparse.Namespace()

        def fake_insert(*args, **kwargs):
            raise RuntimeError("simulated DB error")

        monkeypatch.setattr(member_lib, "insert", fake_insert)
        monkeypatch.setattr(member_lib, "database", type("M", (), {
            "getpool": staticmethod(lambda args: None),
            "connect": staticmethod(lambda args, pool=None: _NullCtx()),
        })())

        result = _ensure_daemon_member(args, "moniker:casino")
        assert result is None


class _NullCtx:
    """Minimal no-op context manager for mocking database.connect."""

    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False
