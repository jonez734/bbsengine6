"""
Pure unit tests for :class:`bbsengine6.services.member.MemberService`.

Originally lived at ``casino/tests/test_member_services.py`` and was moved
here after commit bfb2a07 decoupled bank, member, channel, and postoffice
services out of casino. The mock-based unit tests belong in
``bbsengine6`` because they exercise the canonical service
implementation in :mod:`bbsengine6.services.member`.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src")

pytestmark = pytest.mark.unit


class TestMemberServicesMocked(unittest.IsolatedAsyncioTestCase):
    """Pure unit tests for ``MemberService`` with the DAL mocked out."""

    async def asyncSetUp(self):
        """Set up an args mock for ``MemberService``."""
        self.mock_args = MagicMock()

    async def test_get_profile_returns_attrs(self):
        """``get_profile`` returns the merged member attributes."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "get_profile") as mock_get:
            mock_get.return_value = {
                "moniker": "testuser",
                "email": "test@test.local",
                "tier": "silver",
                "attrs": {"tier": "silver", "preferences": {}},
            }

            result = mock_service.get_profile("testuser")
            self.assertEqual(result["tier"], "silver")

    async def test_update_profile_merges_attrs(self):
        """``update_profile`` returns the success envelope."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "update_profile") as mock_update:
            mock_update.return_value = {"success": True, "message": "Profile updated"}

            result = mock_service.update_profile("testuser", {"tier": "gold"})
            self.assertTrue(result["success"])

    async def test_tier_transitions(self):
        """``set_tier`` can change a member's tier."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "set_tier") as mock_set:
            mock_set.return_value = True

            result = mock_service.set_tier("testuser", "diamond")
            self.assertTrue(result)

    async def test_get_referral_code_returns_string(self):
        """``get_referral_code`` returns the configured refcode."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "get_referral_code") as mock_code:
            mock_code.return_value = "REFCODE123"

            result = mock_service.get_referral_code("testuser")
            self.assertEqual(result, "REFCODE123")

    async def test_get_referrals_returns_list(self):
        """``get_referrals`` returns the list of referred members."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "get_referrals") as mock_refs:
            mock_refs.return_value = [
                {"moniker": "user1", "email": "user1@test.local"},
                {"moniker": "user2", "email": "user2@test.local"},
            ]

            result = mock_service.get_referrals("testuser")
            self.assertEqual(len(result), 2)

    async def test_use_referral_code_success(self):
        """``use_referral_code`` records a successful referral."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "use_referral_code") as mock_use:
            mock_use.return_value = {
                "success": True,
                "message": "Referral recorded",
                "referrer": "referrer1",
            }

            result = mock_service.use_referral_code("testuser", "REFCODE123")
            self.assertTrue(result["success"])

    async def test_use_referral_code_invalid_code(self):
        """``use_referral_code`` rejects unknown codes with a clear envelope."""
        from bbsengine6.services.member import MemberService

        mock_service = MemberService(self.mock_args)

        with patch.object(mock_service, "use_referral_code") as mock_use:
            mock_use.return_value = {"success": False, "message": "Invalid referral code"}

            result = mock_service.use_referral_code("testuser", "INVALID")
            self.assertFalse(result["success"])
            self.assertEqual(result["message"], "Invalid referral code")


if __name__ == "__main__":
    unittest.main()
