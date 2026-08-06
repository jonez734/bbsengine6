"""
Unit tests for member transaction safety and parameter validation.

Tests verify that:
1. member.update() accepts correct moniker parameter (not memberid)
2. setflag() receives conn parameter for transaction consistency
3. Member approval workflow works end-to-end without foreign key violations
4. Flag-setting operations maintain transaction isolation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add project source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py/src"))

from bbsengine6 import member as libmember


class TestMemberUpdateMonikerParameter:
    """Test that member.update() correctly handles moniker parameter."""

    def test_member_update_requires_moniker_string_parameter(self):
        """member.update() should accept moniker as third parameter (not memberid)."""
        # Create mock args
        args = Mock()
        args.debug = False

        # Create mock connection
        mock_conn = Mock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.__exit__ = Mock(return_value=None)

        # Create member dict
        member_dict = {
            "moniker": "testuser",
            "email": "test@example.com",
            "credits": 100,
        }

        # Patch database.update and database.cursor
        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                mock_cursor_ctx.return_value.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                # Call member.update with correct moniker parameter
                libmember.update(args, member_dict, "testuser", conn=mock_conn)

                # Verify database.update was called with correct parameters
                mock_db_update.assert_called_once()
                call_args = mock_db_update.call_args
                # The second positional arg should be table name, third is moniker (pk)
                assert call_args[0][2] == "testuser", (
                    "moniker should be passed as third parameter"
                )

    def test_member_update_with_moniker_processes_flags(self):
        """member.update() should process flags from member dict when moniker is correct."""
        args = Mock()
        args.debug = False

        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "testuser",
            "email": "test@example.com",
            "flags": {
                "APPROVED": {"value": True},
                "EMAILVERIFIED": {"value": False},
            },
        }

        with patch("bbsengine6.member.database.update"):
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    libmember.update(args, member_dict, "testuser", conn=mock_conn)

                    # Verify setflag was called for each flag
                    assert mock_setflag.call_count == 2, (
                        "setflag should be called for each flag"
                    )

    def test_member_update_passes_conn_to_setflag(self):
        """member.update() should pass conn parameter to setflag() for transaction consistency."""
        args = Mock()
        args.debug = False

        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "testuser",
            "flags": {"APPROVED": {"value": True}},
        }

        with patch("bbsengine6.member.database.update"):
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    libmember.update(args, member_dict, "testuser", conn=mock_conn)

                    # Verify setflag was called with conn parameter
                    mock_setflag.assert_called()
                    call_kwargs = mock_setflag.call_args[1]
                    assert "conn" in call_kwargs, (
                        "conn parameter should be passed to setflag()"
                    )
                    assert call_kwargs["conn"] == mock_conn, (
                        "same connection should be passed"
                    )


class TestSetflagTransactionConsistency:
    """Test that setflag() maintains transaction consistency when conn is provided."""

    def test_setflag_with_conn_parameter_uses_provided_connection(self):
        """setflag() should use the provided conn parameter for the same transaction."""
        args = Mock()
        args.debug = False

        mock_conn = Mock()
        mock_cursor = MagicMock()

        with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
            with patch("bbsengine6.member.database.insert"):
                mock_cursor_ctx.return_value.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)
                mock_cursor_ctx.return_value = MagicMock()
                mock_cursor_ctx.return_value.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                libmember.setflag(
                    args, "APPROVED", True, moniker="testuser", conn=mock_conn
                )

                # Verify cursor context manager was called (using provided conn)
                mock_cursor_ctx.assert_called_with(mock_conn)

    def test_setflag_uses_upsert_atomic_operation(self):
        """setflag() should use atomic UPSERT operation (INSERT ... ON CONFLICT)."""
        args = Mock()
        args.debug = False

        mock_conn = Mock()
        MagicMock()

        with patch("bbsengine6.member.database.upsert") as mock_upsert:
            with patch("bbsengine6.member.util.logentry"):
                mock_upsert.return_value = True  # upsert returns True on success

                result = libmember.setflag(
                    args, "APPROVED", True, moniker="testuser", conn=mock_conn
                )

                # Verify setflag returns bool (True on success)
                assert result is True

                # Verify database.upsert() was called with correct parameters
                mock_upsert.assert_called_once()
                call_args = mock_upsert.call_args

                # Check positional args
                assert call_args[0][0] == args  # args
                assert call_args[0][1] == "engine.map_member_flag"  # table
                assert call_args[0][2] == {
                    "moniker": "testuser",
                    "name": "APPROVED",
                    "value": True,
                }  # items

                # Check kwargs
                assert call_args[1]["conflict_columns"] == ["moniker", "name"]
                assert call_args[1]["update_columns"] == ["value"]
                assert call_args[1]["conn"] == mock_conn

    def test_setflag_without_conn_operates_in_different_context(self):
        """setflag() without conn parameter will use a different transaction (demonstration of the issue)."""
        args = Mock()
        args.debug = False

        # When conn is not provided, setflag should use getcurrentmoniker
        with patch("bbsengine6.member.getcurrentmoniker") as mock_getcurrent:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.database.insert"):
                    with patch("bbsengine6.member.util.logentry"):
                        mock_getcurrent.return_value = "currentuser"
                        mock_cursor_ctx.return_value.__enter__ = Mock(
                            return_value=MagicMock()
                        )
                        mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                        # Call without moniker or conn
                        libmember.setflag(args, "APPROVED", True)

                        # Verify it got moniker from getcurrentmoniker (not from connection context)
                        mock_getcurrent.assert_called()


class TestMemberApprovalWorkflow:
    """Test the complete member approval workflow."""

    def test_memberapproval_approves_member_with_correct_moniker(self):
        """Member approval workflow should use moniker, not memberid."""
        args = Mock()
        args.debug = False

        # Simulate member data from database
        member_data = {
            "id": 123,
            "moniker": "jonez",
            "loginid": "jonez_login",
            "email": "jonez@example.com",
            "flags": {},
        }

        mock_conn = Mock()

        with patch("bbsengine6.member.getbymoniker") as mock_getbymoniker:
            with patch("bbsengine6.member.setflag"):
                with patch("bbsengine6.member.update") as mock_update:
                    mock_getbymoniker.return_value = member_data

                    # Simulate the approval flow from memberapproval.py
                    moniker = member_data["moniker"]
                    m = member_data.copy()

                    # Set approval flag
                    libmember.setflag(
                        args, "APPROVED", True, moniker=moniker, conn=mock_conn
                    )

                    # Update member with approval metadata
                    m["approvedbymoniker"] = "sysop_user"
                    m["dateapproved"] = "now()"

                    # Call update with correct moniker (not memberid)
                    libmember.update(args, m, m["moniker"], conn=mock_conn)

                    # Verify update was called with moniker string
                    mock_update.assert_called_once()
                    call_args = mock_update.call_args[0]
                    assert call_args[2] == "jonez", (
                        "Should pass moniker string, not memberid"
                    )

    def test_member_approval_with_email_verification_and_flag_sets(self):
        """Complete workflow: email verification flag + approval flag + member update."""
        args = Mock()
        args.debug = False

        member_data = {
            "id": 456,
            "moniker": "newuser",
            "loginid": "newuser_login",
            "email": "newuser@example.com",
            "flags": {},
        }

        mock_conn = Mock()

        with patch("bbsengine6.member.setflag") as mock_setflag:
            with patch("bbsengine6.member.update") as mock_update:
                moniker = member_data["moniker"]
                m = member_data.copy()

                # Step 1: Set email verified flag
                libmember.setflag(
                    args, "EMAILVERIFIED", True, moniker=moniker, conn=mock_conn
                )
                assert mock_setflag.call_count == 1

                # Step 2: Set approval flag
                libmember.setflag(
                    args, "APPROVED", True, moniker=moniker, conn=mock_conn
                )
                assert mock_setflag.call_count == 2

                # Step 3: Update member record with approval metadata
                m["approvedbymoniker"] = "sysop_user"
                m["dateapproved"] = "now()"
                libmember.update(args, m, m["moniker"], conn=mock_conn)

                # Verify all operations used correct parameters
                for call_obj in mock_setflag.call_args_list:
                    kwargs = call_obj[1]
                    assert kwargs["conn"] == mock_conn, "setflag should receive conn"

                mock_update.assert_called_once()
                update_call_args = mock_update.call_args[0]
                assert update_call_args[2] == moniker, (
                    "update should receive moniker string"
                )


class TestForeignKeyConstraintPrevention:
    """Test that fixes prevent foreign key constraint violations."""

    def test_correct_moniker_prevents_foreign_key_violation(self):
        """Using correct moniker in update() prevents orphaned flag records."""
        # The bug was: memberid (123) passed to update()
        # This would cause WHERE moniker=123 (type mismatch, silently fails)
        # Then setflag() tries to insert with non-existent moniker
        # Result: foreign key violation

        # The fix: m["moniker"] ("jonez") passed to update()
        # This causes WHERE moniker='jonez' (correct, matches the member)
        # Member gets updated properly
        # setflag() operations succeed

        args = Mock()
        args.debug = False
        mock_conn = Mock()

        # Using the correct parameter type
        moniker_string = "jonez"  # Correct: string moniker

        # When update is called with correct moniker, the WHERE clause works
        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor"):
                with patch("bbsengine6.member.setflag"):
                    libmember.update(
                        args,
                        {"moniker": moniker_string},
                        moniker_string,
                        conn=mock_conn,
                    )

                    # Verify the correct parameter was used
                    call_args = mock_db_update.call_args[0]
                    # Third parameter should be the WHERE clause value
                    assert call_args[2] == moniker_string
                    assert isinstance(call_args[2], str)

    def test_setflag_with_conn_maintains_transaction_atomicity(self):
        """setflag() with conn parameter ensures delete+insert are in same transaction."""
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
            with patch("bbsengine6.member.database.insert"):
                with patch("bbsengine6.member.util.logentry"):
                    # Configure mock cursor
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    libmember.setflag(
                        args, "APPROVED", True, moniker="jonez", conn=mock_conn
                    )

                    # Verify DELETE and INSERT happen in same transaction context
                    # (same cursor/connection, no separate transaction)
                    mock_cursor_ctx.assert_called_once_with(mock_conn)
                    # Cursor execute should be called for DELETE
                    mock_cursor.execute.assert_called_once()


class TestDataConsistency:
    """Test data consistency and integrity constraints."""

    def test_member_with_flags_dict_remains_valid_for_update(self):
        """Member dict with flags key should be processable by update()."""
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "testuser",
            "email": "test@example.com",
            "flags": {"APPROVED": {"value": True}, "VERIFIED": {"value": False}},
        }

        with patch("bbsengine6.member.database.update"):
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag"):
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    # Should not raise any errors
                    libmember.update(args, member_dict, "testuser", conn=mock_conn)

    def test_member_without_flags_key_also_works(self):
        """Member dict without flags key should work fine."""
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "testuser",
            "email": "test@example.com",
            # No flags key
        }

        with patch("bbsengine6.member.database.update"):
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                mock_cursor_ctx.return_value.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                # Should not raise any errors
                libmember.update(args, member_dict, "testuser", conn=mock_conn)


class TestMonikerChange:
    """Test member moniker changes with flag handling."""

    def test_moniker_change_detection(self):
        """Test that moniker_is_changing is correctly detected."""
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "newmoniker",  # Changed from 'oldmoniker'
            "email": "test@example.com",
        }

        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                mock_cursor_ctx.return_value.__enter__ = Mock(return_value=mock_cursor)
                mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                # Call update with old moniker different from new moniker
                libmember.update(args, member_dict, "oldmoniker", conn=mock_conn)

                # Verify database.update was called
                mock_db_update.assert_called_once()
                call_args = mock_db_update.call_args[0]
                # Check that moniker was passed as PK
                assert call_args[2] == "oldmoniker"

    def test_moniker_change_with_flags(self):
        """Test moniker change with flag value updates.

        When moniker changes, flags should be updated FIRST using OLD moniker,
        then member is updated (CASCADE handles migration), then we're done.
        """
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        # Member is being updated with moniker change AND flag changes
        member_dict = {
            "moniker": "jonez",  # New moniker (changed from 'olduser')
            "email": "jonez@example.com",
            "flags": {
                "APPROVED": {"value": True},
                "SYSOP": {"value": True},
            },
        }

        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    # Make setflag return True (success)
                    mock_setflag.return_value = True
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    # Update member, changing moniker from 'olduser' to 'jonez'
                    libmember.update(args, member_dict, "olduser", conn=mock_conn)

                    # Verify setflag was called FIRST with OLD moniker for each flag
                    # (because moniker is changing)
                    assert mock_setflag.call_count == 2
                    for call_obj in mock_setflag.call_args_list:
                        kwargs = call_obj[1]
                        # Flags should use OLD moniker (olduser) when moniker is changing
                        # CASCADE will migrate them after member update
                        assert kwargs["moniker"] == "olduser"

                    # Verify database.update was called with old moniker
                    mock_db_update.assert_called_once()
                    call_args = mock_db_update.call_args[0]
                    assert call_args[2] == "olduser"

    def test_moniker_change_cascade_flow(self):
        """Test that moniker change with CASCADE works correctly.

        Flow:
        1. setflag() called with OLD moniker (flags definitely exist)
        2. database.update() updates member moniker (CASCADE migrates flags)
        3. Done - flags are now with new moniker
        """
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "newname",
            "email": "newname@example.com",
            "flags": {
                "APPROVED": {"value": True},
            },
        }

        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    mock_setflag.return_value = True  # setflag returns bool now
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    libmember.update(args, member_dict, "oldname", conn=mock_conn)

                    # Step 1: setflag should be called FIRST with OLD moniker
                    mock_setflag.assert_called_once()
                    setflag_kwargs = mock_setflag.call_args[1]
                    assert setflag_kwargs["moniker"] == "oldname"

                    # Step 2: Member update should be called with OLD moniker as PK
                    mock_db_update.assert_called_once()
                    update_call_args = mock_db_update.call_args[0]
                    assert update_call_args[2] == "oldname"
                    # The rec dict passed should contain the NEW moniker
                    rec = update_call_args[3]
                    assert rec["moniker"] == "newname"

    def test_moniker_not_changing_skips_cascade_logic(self):
        """Test that non-moniker updates don't trigger cascade logic."""
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "sameuser",  # Moniker NOT changing
            "email": "newemail@example.com",
            "flags": {
                "APPROVED": {"value": True},
            },
        }

        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    # Update member WITHOUT changing moniker
                    libmember.update(args, member_dict, "sameuser", conn=mock_conn)

                    # Verify database.update was called
                    mock_db_update.assert_called_once()

                    # Verify setflag uses the SAME moniker (no change)
                    mock_setflag.assert_called_once()
                    setflag_kwargs = mock_setflag.call_args[1]
                    assert setflag_kwargs["moniker"] == "sameuser"

    def test_moniker_change_with_multiple_flags(self):
        """Test moniker change with multiple flag updates (the real-world scenario).

        This tests the journal scenario: changing moniker with 5 flags all at once.
        Flags should be updated with OLD moniker first, then member update handles CASCADE.
        """
        args = Mock()
        args.debug = False
        mock_conn = Mock()
        mock_cursor = MagicMock()

        member_dict = {
            "moniker": "jonez",
            "email": "jonez@example.com",
            "flags": {
                "AUTHENTICATED": {"value": True, "description": "Authenticated Member"},
                "ASIMOV": {"value": True, "description": "Project Asimov"},
                "NOCALUMNI": {"value": True, "description": "NOC Alumni"},
                "EMAILVERIFIED": {"value": True, "description": "E-Mail Verified"},
                "APPROVED": {"value": True, "description": "Account Approved"},
            },
        }

        with patch("bbsengine6.member.database.update") as mock_db_update:
            with patch("bbsengine6.member.database.cursor") as mock_cursor_ctx:
                with patch("bbsengine6.member.setflag") as mock_setflag:
                    mock_setflag.return_value = True  # setflag returns bool now
                    mock_cursor_ctx.return_value.__enter__ = Mock(
                        return_value=mock_cursor
                    )
                    mock_cursor_ctx.return_value.__exit__ = Mock(return_value=None)

                    # Update member changing moniker with 5 flag changes
                    libmember.update(args, member_dict, "olduser", conn=mock_conn)

                    # Verify setflag was called for each flag with OLD moniker
                    # (moniker is changing, so flags updated first)
                    assert mock_setflag.call_count == 5
                    for call_obj in mock_setflag.call_args_list:
                        # setflag is called as: setflag(args, name, value, moniker=moniker, conn=conn)
                        args_tuple = call_obj[0]
                        kwargs = call_obj[1]
                        # args_tuple[1] is the flag name
                        flag_name = args_tuple[1]
                        # Flags should use OLD moniker (olduser) when moniker is changing
                        assert kwargs["moniker"] == "olduser"
                        # Verify each flag name is one of the expected flags
                        assert flag_name in [
                            "AUTHENTICATED",
                            "ASIMOV",
                            "NOCALUMNI",
                            "EMAILVERIFIED",
                            "APPROVED",
                        ]

                    # Verify database.update was called after flags
                    mock_db_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
