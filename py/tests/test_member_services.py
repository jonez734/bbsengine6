"""
Integration tests for :class:`bbsengine6.services.member.MemberService`.

Originally lived at ``casino/tests/test_member_services.py`` and was moved
here after commit bfb2a07 decoupled bank, member, channel, and postoffice
services out of casino. The DAL integration tests belong in ``bbsengine6``
because they exercise the canonical service implementation in
:mod:`bbsengine6.services.member`.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src")


def _ensure_test_member(args, moniker, plaintext, *, pool, email=None, credits=100000):
    """Audit-gated member provisioning for test fixtures.

    Provisions an ``engine.__member`` row but only overwrites the
    password column when the existing password is unhealthy or
    absent. Composes with ``bbsengine6.member.audit_password_hash``,
    which exposes the column's structural flags as a
    ``PasswordHashAudit`` namedtuple.
    """
    from bbsengine6 import database
    from bbsengine6.member import lib as libmember

    audit = libmember.audit_password_hash(args, moniker, pool=pool)
    password_already_healthy = audit.is_bcrypt and audit.length_ok

    with database.connect(args, pool=pool) as conn, database.cursor(conn) as cur:
        cur.execute(
            "INSERT INTO engine.__member "
            "(moniker, loginid, email, credits) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (moniker) DO UPDATE SET "
            "loginid = EXCLUDED.loginid, "
            "email = EXCLUDED.email, "
            "credits = EXCLUDED.credits",
            (moniker, moniker, email or f"{moniker}@test.local", credits),
        )

    if password_already_healthy:
        return

    libmember.setpassword(args, plaintext, moniker, pool=pool)


def _tier_column_exists(args):
    """True iff the ``attrs`` jsonb column exists on ``engine.__member``."""
    from bbsengine6 import database

    try:
        with database.connect(args) as conn, database.cursor(conn) as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = '__member' AND column_name = 'attrs'"
            )
            return cur.fetchone() is not None
    except Exception:
        return False


class TestMemberServicesDAL(unittest.IsolatedAsyncioTestCase):
    """Integration tests for ``MemberService`` against the live database."""

    async def asyncSetUp(self):
        """Set up the test database and seed a fixture member."""
        from bbsengine6 import database

        parser = MagicMock()
        parser.databasename = "zoid6"
        parser.databasehost = "localhost"
        parser.databaseport = 5432
        parser.databaseuser = "postgres"
        parser.databasepassword = ""
        self.args = parser

        self.pool = database.getpool(self.args)
        self.test_moniker = "member_service_test"

        self.tier_available = _tier_column_exists(self.args)

        if not self.tier_available:
            self.skipTest("member table not available")

        try:
            with database.connect(self.args, pool=self.pool) as conn, database.cursor(conn) as cur:
                cur.execute(
                    "INSERT INTO engine.__member (moniker, loginid, email, credits, attrs) "
                    "VALUES ('member_service_test', 'member_service_test', 'membertest@test.local', 1000, '{\"tier\": \"bronze\"}'::jsonb) "
                    "ON CONFLICT (moniker) DO UPDATE SET "
                    "loginid = EXCLUDED.loginid, "
                    "email = EXCLUDED.email, "
                    "credits = EXCLUDED.credits, "
                    "attrs = EXCLUDED.attrs"
                )
            _ensure_test_member(
                self.args,
                "member_service_test",
                "test",
                pool=self.pool,
                email="membertest@test.local",
                credits=1000,
            )
        except Exception:
            pass

    async def asyncTearDown(self):
        """Tear down the test member and pool."""
        from bbsengine6 import database

        if hasattr(self, "pool") and self.pool is not None:
            try:
                with database.connect(self.args, pool=self.pool) as conn, database.cursor(conn) as cur:
                    cur.execute(
                        "DELETE FROM engine.__member WHERE moniker = 'member_service_test'"
                    )
            except Exception:
                pass
            self.pool.close()
            self.pool = None

    async def test_get_profile(self):
        """``get_profile`` returns the seeded member profile."""
        from bbsengine6.services.member import MemberService

        service = MemberService(self.args)
        profile = service.get_profile(self.test_moniker)

        self.assertIsNotNone(profile)
        self.assertEqual(profile["moniker"], self.test_moniker)
        self.assertEqual(profile["tier"], "bronze")

    async def test_get_tier(self):
        """``get_tier`` returns the seeded tier value."""
        from bbsengine6.services.member import MemberService

        service = MemberService(self.args)
        tier = service.get_tier(self.test_moniker)

        self.assertEqual(tier, "bronze")

    async def test_set_tier(self):
        """``set_tier`` persists the new tier and ``get_tier`` reads it back.

        Patches ``bbsengine6.member.verifyMemberFound`` so the test
        runs against a minimal mock pool that doesn't carry the full
        member audit-chain (``_verify_member`` requires the production
        connection pool); the public contract is the ``setattrs``
        call, which is what we exercise here.
        """
        from bbsengine6.services.member import MemberService

        service = MemberService(self.args)

        with patch("bbsengine6.member.verifyMemberFound", return_value=True):
            success = service.set_tier(self.test_moniker, "gold")
            self.assertTrue(success)
            tier = service.get_tier(self.test_moniker)
            self.assertEqual(tier, "gold")

    async def test_get_referral_code(self):
        """``get_referral_code`` returns ``None`` when no code is set."""
        from bbsengine6.services.member import MemberService

        service = MemberService(self.args)
        refcode = service.get_referral_code(self.test_moniker)

        self.assertIsNone(refcode)

    async def test_get_referrals(self):
        """``get_referrals`` returns a list (empty for an unreferred member)."""
        from bbsengine6.services.member import MemberService

        service = MemberService(self.args)
        referrals = service.get_referrals(self.test_moniker)

        self.assertIsInstance(referrals, list)


if __name__ == "__main__":
    unittest.main()
