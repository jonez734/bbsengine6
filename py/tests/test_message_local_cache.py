# test_message_local_cache.py
# Tests for the local unread-count cache (server-push consumers).

import pytest


class TestLocalUnreadCache:
    """The local cache backs getch.py/bottombar.py without DB hits."""

    def test_cache_initially_minus_one(self):
        """Unread count for a new moniker returns -1 (cold cache)."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        assert message.get_local_unread_count("nonexistent_moniker_xyz") == -1

    def test_set_and_get(self):
        """Set then get returns the same value."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("alice", 5)
        assert message.get_local_unread_count("alice") == 5

    def test_set_clamps_to_zero(self):
        """Negative values are clamped to zero."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("alice", -3)
        assert message.get_local_unread_count("alice") == 0

    def test_bump_increments(self):
        """Bump with positive delta increases the count."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("bob", 2)
        message.bump_local_unread_count("bob", 1)
        assert message.get_local_unread_count("bob") == 3

    def test_bump_decrements(self):
        """Bump with negative delta decreases the count."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("bob", 5)
        message.bump_local_unread_count("bob", -2)
        assert message.get_local_unread_count("bob") == 3

    def test_bump_clamps_to_zero(self):
        """Bump that would go below zero is clamped."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("bob", 1)
        message.bump_local_unread_count("bob", -10)
        assert message.get_local_unread_count("bob") == 0

    def test_bump_starts_from_zero_when_cold(self):
        """Bump on a cold cache starts from 0."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.bump_local_unread_count("carol", 1)
        assert message.get_local_unread_count("carol") == 1

    def test_clear(self):
        """Clear resets all cached values."""
        from bbsengine6 import message

        message.set_local_unread_count("dave", 7)
        message.clear_local_unread_cache()
        assert message.get_local_unread_count("dave") == -1

    def test_separate_monikers(self):
        """Different monikers have independent counters."""
        from bbsengine6 import message

        message.clear_local_unread_cache()
        message.set_local_unread_count("eve", 1)
        message.set_local_unread_count("frank", 2)
        assert message.get_local_unread_count("eve") == 1
        assert message.get_local_unread_count("frank") == 2
