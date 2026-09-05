"""
Tests for the moniker reservation / namespacing policy.

The namespacing foundation (Phase 1.5) added four layers of protection:

1. SQL regex: chk_member_moniker_format allows ``<module>:<purpose>`` in
   addition to flat names.
2. Python validation: ``_validate_moniker_shape`` rejects flat reserved
   names AND namespaced names from the standard registration path.
3. Bypass: ``register_module_member`` accepts namespaced-lowercase-shape
   only.
4. Reserved list: ``RESERVED_MONIKERS = {"sysop", "term", "web", "bed"}``.

These tests cover the Python layers. The SQL layer is exercised by the
existing test_channel_announce_only.py integration tests.
"""

from __future__ import annotations

import argparse

import pytest

from bbsengine6.member.lib import (
    RESERVED_MONIKERS,
    _validate_moniker_shape,
    is_namespaced_moniker,
    register_module_member,
)


# ---------------------------------------------------------------------------
# Reserved list
# ---------------------------------------------------------------------------


class TestReservedMonikersList:
    """The shipped reservation list contains exactly the four PG roles."""

    def test_contains_shipped_role_names(self):
        assert "sysop" in RESERVED_MONIKERS
        assert "term" in RESERVED_MONIKERS
        assert "web" in RESERVED_MONIKERS
        assert "bed" in RESERVED_MONIKERS

    def test_does_not_contain_module_prefix(self):
        # Namespacing convention means modules own their prefix without
        # needing a bbsengine6 reservation. 'zoid6' would be misleading
        # here because it's an installer name, not a bbsengine6 concept.
        assert "zoid6" not in RESERVED_MONIKERS

    def test_does_not_contain_human_names(self):
        # Common Unix-style names were discussed but rejected: namespacing
        # is the structural defense and these names are too likely to
        # collide with legitimate users.
        for name in ("admin", "root", "daemon", "bbs", "system"):
            assert name not in RESERVED_MONIKERS


# ---------------------------------------------------------------------------
# is_namespaced_moniker predicate
# ---------------------------------------------------------------------------


class TestIsNamespacedMoniker:
    """The predicate detects namespaced form."""

    @pytest.mark.parametrize("moniker", ["alice", "zoid6", "sysop", ""])
    def test_flat_returns_false(self, moniker):
        assert is_namespaced_moniker(moniker) is False

    @pytest.mark.parametrize(
        "moniker", ["zoid6:casino", "empyre:router", "system:bbs"]
    )
    def test_namespaced_returns_true(self, moniker):
        assert is_namespaced_moniker(moniker) is True


# ---------------------------------------------------------------------------
# _validate_moniker_shape (standard registration path)
# ---------------------------------------------------------------------------


class TestValidateMonikerShape:
    """Standard registration rejects reserved AND namespaced monikers."""

    @pytest.mark.parametrize("name", ["sysop", "term", "web", "bed"])
    def test_rejects_reserved_flat(self, name):
        with pytest.raises(ValueError, match="reserved for system use"):
            _validate_moniker_shape(name)

    def test_rejects_namespaced_via_standard_path(self):
        with pytest.raises(ValueError, match="namespaced"):
            _validate_moniker_shape("zoid6:casino")

    def test_allows_normal_flat(self):
        # Should not raise.
        _validate_moniker_shape("alice")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_moniker_shape("")

    def test_rejects_non_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_moniker_shape(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# register_module_member bypass path
# ---------------------------------------------------------------------------


class TestRegisterModuleMember:
    """Bypass enforces namespaced-lowercase-shape."""

    def _args(self) -> argparse.Namespace:
        # Minimal stub. The function's first checks (shape / lowercase)
        # raise before any DB access, so we don't need a real DB pool.
        return argparse.Namespace()

    def test_rejects_flat_form(self):
        with pytest.raises(ValueError, match="namespaced moniker"):
            register_module_member(self._args(), "casino_router")

    def test_rejects_uppercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            register_module_member(self._args(), "Zoid6:casino")

    def test_rejects_bad_shape(self):
        with pytest.raises(ValueError, match="<module>:<purpose>"):
            register_module_member(self._args(), ":casino")

    def test_rejects_just_colon(self):
        with pytest.raises(ValueError, match="<module>:<purpose>"):
            register_module_member(self._args(), "zoid6:")

    def test_accepts_namespaced_shape(self):
        # The shape/lowercase/namespaced gates should all pass. The
        # ``_skip_shape_validation`` flag added to ``insert`` lets the
        # bypass path through without re-validating. Any error after
        # that point is from the underlying insert (e.g. DB unreachable,
        # missing schema, missing FK) — NOT from shape validation.
        try:
            register_module_member(self._args(), "zoid6:casino")
        except ValueError as e:
            # Shape errors must NOT come through here. If they do, the
            # bypass is broken.
            msg = str(e)
            assert "namespaced moniker" not in msg
            assert "lowercase" not in msg
            assert "expected shape" not in msg
            assert "reserved for module bootstrap" not in msg
            pytest.fail(f"bypass path leaked a shape validation error: {msg}")
        except Exception:
            # Non-ValueError exceptions (DB errors, FK violations, etc.)
            # are expected when the test runs without a real DB.
            pass
