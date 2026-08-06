"""
Tests for the generic invite code system.

Covers the bbsengine6.invite DAL and the bbsengine6.services.invite
InviteService wrapper. Integration tests run against the zoid6test
database; per-test data is isolated by the conftest's autouse
transaction rollback.
"""

from __future__ import annotations

import argparse
import getpass
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from bbsengine6 import database
from bbsengine6.services.invite import InviteService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_test_args(databasename: str = "zoid6test") -> argparse.Namespace:
    """Build args for invite tests against the zoid6test DB."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture(scope="function")
def test_args() -> argparse.Namespace:
    return make_test_args()


@pytest.fixture(scope="function")
def invite_service(test_args: argparse.Namespace) -> InviteService:
    return InviteService(test_args)


def _test_user(index: int) -> str:
    """The dynamic test monikers created by conftest.create_test_users."""
    return f"test_{getpass.getuser()}_{index}"


def _unique_resourceid(suffix: str) -> str:
    """Per-test unique resource id to avoid cross-test interference."""
    return f"test_{getpass.getuser()}_res_{suffix}_{uuid.uuid4().hex[:8]}"


def _insert_casino_table(
    args: argparse.Namespace, moniker: str, owner: str
) -> None:
    """Insert a minimal casino.__table row so the FK can resolve.

    casino.__table FKs to bank.__account(id) for accountid and to
    engine.__member for ownermoniker. We use a NULL accountid to avoid
    the bank dependency in this test.
    """
    with database.connect(args) as conn, database.cursor(conn) as cur:
        cur.execute(
            database.query(
                """INSERT INTO $casino.__table
                           (moniker, type, ownermoniker, accountid)
                       VALUES (:moniker, 'test', :ownermoniker, NULL)
                       ON CONFLICT (moniker) DO NOTHING""",
                moniker=moniker,
                ownermoniker=owner,
            )
        )


def _delete_casino_table(args: argparse.Namespace, moniker: str) -> None:
    with database.connect(args) as conn, database.cursor(conn) as cur:
        cur.execute(
            database.query(
                "DELETE FROM $casino.__table WHERE moniker = :moniker",
                moniker=moniker,
            )
        )


# ---------------------------------------------------------------------------
# create_invite
# ---------------------------------------------------------------------------


class TestCreateInvite:
    """create_invite() inserts a row and returns the code + id."""

    def test_create_with_random_code(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("random")
        result = invite_service.create_invite(
            module="casino",
            resourceid=resourceid,
            createdbymoniker=_test_user(1),
        )
        assert result["success"] is True
        assert isinstance(result["id"], int)
        assert result["code"] and len(result["code"]) >= 8
        assert result["module"] == "casino"
        assert result["resourceid"] == resourceid
        assert result["datecreated"] is not None
        assert result["dateexpires"] is None

    def test_create_with_explicit_code(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("explicit")
        result = invite_service.create_invite(
            module="casino",
            resourceid=resourceid,
            createdbymoniker=_test_user(1),
            code="myCustomCode",
        )
        assert result["success"] is True
        assert result["code"] == "myCustomCode"

    def test_create_with_expiry(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("expiry")
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        result = invite_service.create_invite(
            module="empyre",
            resourceid=resourceid,
            createdbymoniker=_test_user(2),
            dateexpires=expiry,
        )
        assert result["success"] is True
        assert result["dateexpires"] is not None

    def test_create_with_casino_fk(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        table_moniker = f"test_{getpass.getuser()}_casino_{uuid.uuid4().hex[:8]}"
        try:
            _insert_casino_table(test_args, table_moniker, _test_user(1))
            result = invite_service.create_invite(
                module="casino",
                resourceid=table_moniker,
                createdbymoniker=_test_user(1),
                casinotablemoniker=table_moniker,
            )
            assert result["success"] is True
        finally:
            _delete_casino_table(test_args, table_moniker)

    def test_create_duplicate_active_code_rejected(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("dup")
        first = invite_service.create_invite(
            module="casino",
            resourceid=resourceid,
            createdbymoniker=_test_user(1),
            code="DUPCODE1",
        )
        assert first["success"] is True
        second = invite_service.create_invite(
            module="casino",
            resourceid=resourceid,
            createdbymoniker=_test_user(1),
            code="DUPCODE1",
        )
        assert second["success"] is False

    def test_create_missing_args_returns_error(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        result = invite_service.create_invite(
            module="",
            resourceid="x",
            createdbymoniker=_test_user(1),
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# get_invites
# ---------------------------------------------------------------------------


class TestGetInvites:
    """get_invites() lists invites for a module/resource."""

    def test_lists_active_invites(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("list")
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="LISTCODE1",
        )
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="LISTCODE2",
        )
        result = invite_service.list_invites(module="casino", resourceid=resourceid)
        assert result["success"] is True
        assert result["count"] == 2
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"LISTCODE1", "LISTCODE2"}

    def test_default_excludes_used(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("default_used")
        a = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="USEDA",
        )
        b = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="USEDB",
        )
        invite_service.use_invite(a["id"], _test_user(2))

        result = invite_service.list_invites(module="casino", resourceid=resourceid)
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"USEDB"}
        assert b["id"] in {inv["id"] for inv in result["invites"]}

    def test_default_excludes_revoked(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("default_revoked")
        a = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REVOKEA",
        )
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REVOKEB",
        )
        invite_service.revoke_invite(a["id"])

        result = invite_service.list_invites(module="casino", resourceid=resourceid)
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"REVOKEB"}

    def test_include_used_flag(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("include_used")
        a = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="INCUSED",
        )
        invite_service.use_invite(a["id"], _test_user(2))

        result = invite_service.list_invites(
            module="casino", resourceid=resourceid, include_used=True
        )
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"INCUSED"}

    def test_include_revoked_flag(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("include_revoked")
        a = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="INCREVOKED",
        )
        invite_service.revoke_invite(a["id"])

        result = invite_service.list_invites(
            module="casino", resourceid=resourceid, include_revoked=True
        )
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"INCREVOKED"}

    def test_isolates_by_resource(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        a = _unique_resourceid("iso_a")
        b = _unique_resourceid("iso_b")
        invite_service.create_invite(
            module="casino", resourceid=a,
            createdbymoniker=_test_user(1), code="ISOA",
        )
        invite_service.create_invite(
            module="casino", resourceid=b,
            createdbymoniker=_test_user(1), code="ISOB",
        )
        result = invite_service.list_invites(module="casino", resourceid=a)
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"ISOA"}

    def test_isolates_by_module(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("module")
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="MCAS",
        )
        invite_service.create_invite(
            module="empyre", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="MEMP",
        )
        result = invite_service.list_invites(module="casino", resourceid=resourceid)
        codes = {inv["code"] for inv in result["invites"]}
        assert codes == {"MCAS"}


# ---------------------------------------------------------------------------
# validate_invite
# ---------------------------------------------------------------------------


class TestValidateInvite:
    """validate_invite() returns the invite if usable, else None."""

    def test_valid_invite_returned(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("valid")
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="VAL1",
        )
        result = invite_service.validate_invite(
            module="casino", resourceid=resourceid, code="VAL1"
        )
        assert result["success"] is True
        assert result["invite"] is not None
        assert result["invite"]["code"] == "VAL1"

    def test_wrong_code_returns_invalid(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("wrong_code")
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="RIGHT",
        )
        result = invite_service.validate_invite(
            module="casino", resourceid=resourceid, code="WRONG"
        )
        assert result["success"] is False
        assert result["invite"] is None

    def test_wrong_module_returns_invalid(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("wrong_mod")
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="WMOD",
        )
        result = invite_service.validate_invite(
            module="empyre", resourceid=resourceid, code="WMOD"
        )
        assert result["success"] is False
        assert result["invite"] is None

    def test_used_invite_invalid(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("used")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="USEDVAL",
        )
        invite_service.use_invite(created["id"], _test_user(2))
        result = invite_service.validate_invite(
            module="casino", resourceid=resourceid, code="USEDVAL"
        )
        assert result["success"] is False
        assert result["invite"] is None

    def test_revoked_invite_invalid(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("revoked")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REVVAL",
        )
        invite_service.revoke_invite(created["id"])
        result = invite_service.validate_invite(
            module="casino", resourceid=resourceid, code="REVVAL"
        )
        assert result["success"] is False
        assert result["invite"] is None

    def test_expired_invite_invalid(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("expired")
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1),
            code="EXPVAL",
            dateexpires=past,
        )
        result = invite_service.validate_invite(
            module="casino", resourceid=resourceid, code="EXPVAL"
        )
        assert result["success"] is False
        assert result["invite"] is None


# ---------------------------------------------------------------------------
# mark_used
# ---------------------------------------------------------------------------


class TestMarkUsed:
    """mark_used() sets dateused; idempotent guard on second use."""

    def test_mark_used_success(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("mark_ok")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="MUSE1",
        )
        result = invite_service.use_invite(created["id"], _test_user(2))
        assert result["success"] is True

    def test_mark_used_idempotent(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("mark_idem")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="MUSE2",
        )
        first = invite_service.use_invite(created["id"], _test_user(2))
        second = invite_service.use_invite(created["id"], _test_user(3))
        assert first["success"] is True
        assert second["success"] is False

    def test_mark_used_rejected_on_revoked(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("mark_rev")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="MUSE3",
        )
        invite_service.revoke_invite(created["id"])
        result = invite_service.use_invite(created["id"], _test_user(2))
        assert result["success"] is False

    def test_mark_used_missing_id(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        result = invite_service.use_invite(999_999_999, _test_user(2))
        assert result["success"] is False


# ---------------------------------------------------------------------------
# revoke_invite
# ---------------------------------------------------------------------------


class TestRevokeInvite:
    """revoke_invite() sets revoked; idempotent on second revoke."""

    def test_revoke_success(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("revoke_ok")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REV1",
        )
        result = invite_service.revoke_invite(created["id"])
        assert result["success"] is True

    def test_revoke_idempotent(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("revoke_idem")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REV2",
        )
        first = invite_service.revoke_invite(created["id"])
        second = invite_service.revoke_invite(created["id"])
        assert first["success"] is True
        assert second["success"] is False

    def test_revoke_rejected_on_used(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("revoke_used")
        created = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REV3",
        )
        invite_service.use_invite(created["id"], _test_user(2))
        result = invite_service.revoke_invite(created["id"])
        assert result["success"] is False

    def test_revoke_missing_id(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        result = invite_service.revoke_invite(999_999_999)
        assert result["success"] is False

    def test_reuse_code_after_revoke(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        """A code can be re-issued for the same resource after revoke."""
        resourceid = _unique_resourceid("reuse")
        first = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REUSE",
        )
        invite_service.revoke_invite(first["id"])
        second = invite_service.create_invite(
            module="casino", resourceid=resourceid,
            createdbymoniker=_test_user(1), code="REUSE",
        )
        assert second["success"] is True
        assert second["id"] != first["id"]


# ---------------------------------------------------------------------------
# InviteService wrapper
# ---------------------------------------------------------------------------


class TestInviteServiceWrapper:
    """Service wrapper envelope shape and message-type constants."""

    def test_message_type_constants(self):
        assert InviteService.MESSAGE_INVITE_CREATE == "invite_create"
        assert InviteService.MESSAGE_INVITE_LIST == "invite_list"
        assert InviteService.MESSAGE_INVITE_REVOKE == "invite_revoke"
        assert InviteService.MESSAGE_INVITE_VALIDATE == "invite_validate"
        assert InviteService.MESSAGE_INVITE_USE == "invite_use"

    def test_list_envelope_shape(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        resourceid = _unique_resourceid("env_list")
        result = invite_service.list_invites(module="casino", resourceid=resourceid)
        assert "success" in result
        assert "message" in result
        assert "invites" in result
        assert "count" in result
        assert result["count"] == 0
        assert result["invites"] == []

    def test_validate_envelope_shape(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        result = invite_service.validate_invite(
            module="casino", resourceid="nonexistent_xyz_999", code="X"
        )
        assert result["success"] is False
        assert "invite" in result
        assert result["invite"] is None


# ---------------------------------------------------------------------------
# Casino FK cascade
# ---------------------------------------------------------------------------


class TestCasinoFkCascade:
    """Deleting casino.__table cascades to its engine.__invite rows."""

    def test_invite_deleted_when_table_deleted(
        self, test_args: argparse.Namespace, invite_service: InviteService
    ):
        table_moniker = f"test_{getpass.getuser()}_casino_{uuid.uuid4().hex[:8]}"
        try:
            _insert_casino_table(test_args, table_moniker, _test_user(1))
            created = invite_service.create_invite(
                module="casino",
                resourceid=table_moniker,
                createdbymoniker=_test_user(1),
                casinotablemoniker=table_moniker,
                code="CASCADEME",
            )
            assert created["success"] is True

            # Sanity: invite exists.
            listing = invite_service.list_invites(
                module="casino", resourceid=table_moniker
            )
            assert listing["count"] == 1

            # Delete the casino table; invite should cascade away.
            _delete_casino_table(test_args, table_moniker)

            listing_after = invite_service.list_invites(
                module="casino", resourceid=table_moniker
            )
            assert listing_after["count"] == 0
        finally:
            _delete_casino_table(test_args, table_moniker)
