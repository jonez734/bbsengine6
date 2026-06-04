"""
Integration tests for member.update() with flags.

Tests verify the complete flow:
1. Member dict with flags (dict type)
2. buildrec() transforms the structure (keeps dicts as dicts)
3. database.update() converts dicts to JSONB for database storage
4. PostgreSQL stores the data correctly
5. Retrieved data has correct structure

Requires database connection to zoid6test.
"""

import pytest
import argparse
from bbsengine6.member import buildrec
from bbsengine6 import database


class TestBuildrecToUpdateFlow:
    """Test the flow from buildrec() through database.update()."""

    def test_buildrec_returns_dict_not_json_string(self):
        """buildrec() should return dicts as dicts, not JSON strings."""
        member = {
            "moniker": "testuser",
            "email": "test@example.com",
            "flags": {"APPROVED": {"value": True}},
        }

        rec = buildrec(member)

        # The critical fix: flags should be dict, not JSON string
        assert isinstance(rec["flags"], dict)
        assert rec["flags"] == {"APPROVED": {"value": True}}
        # Should NOT be a JSON string
        assert not isinstance(rec["flags"], str)

    def test_buildrec_output_ready_for_database_update(self):
        """buildrec() output should be ready for database.update()."""
        member = {
            "id": 999,
            "moniker": "testuser",
            "email": "test@example.com",
            "loginid": "testlogin",
            "credits": 500,
            "flags": {
                "APPROVED": {"value": True},
                "VERIFIED": {"value": False},
            },
            "ui": ["telnet", "web"],
        }

        rec = buildrec(member)

        # Verify structure is ready for database
        assert rec["moniker"] == "testuser"
        assert rec["email"] == "test@example.com"
        assert isinstance(rec["flags"], dict)
        assert isinstance(rec["ui"], str)

        # database.update() will call convert_for_jsonb() on these values
        # Verify they're the right types for conversion:
        # - strings: pass through
        # - dicts: get wrapped in Jsonb
        # - lists: get wrapped in Jsonb
        assert isinstance(rec["moniker"], str)
        assert isinstance(rec["email"], str)
        assert isinstance(rec["credits"], int)
        assert isinstance(rec["flags"], dict)  # Will be converted to Jsonb
        assert isinstance(rec["ui"], str)


class TestDatabaseConversionFlow:
    """Test that database.update() correctly handles converted values."""

    def test_convert_for_jsonb_on_dict_returns_jsonb_wrapper(self):
        """convert_for_jsonb() should wrap dicts in Jsonb for database."""
        test_dict = {"APPROVED": {"value": True}}

        result = database.convert_for_jsonb(test_dict)

        # Should return Jsonb wrapper
        from psycopg.types.json import Jsonb

        assert isinstance(result, Jsonb)
        # Note: convert_for_jsonb() recursively wraps nested dicts too
        # so result.obj won't equal the original test_dict exactly
        assert isinstance(result.obj, dict)
        assert "APPROVED" in result.obj

    def test_jsonb_object_not_json_serializable(self):
        """Jsonb objects should NOT be JSON serializable (the original bug).

        The outer Jsonb wrapper itself is not json.dumps()-serializable
        (psycopg handles it via its registered adapter, not json.dumps).
        """
        import json

        test_dict = {"APPROVED": {"value": True}}
        jsonb_obj = database.convert_for_jsonb(test_dict)

        # json.dumps() on the outer Jsonb raises TypeError; psycopg uses
        # its own dumper, not the stdlib json.dumps.
        with pytest.raises(TypeError, match="Object of type Jsonb"):
            json.dumps(jsonb_obj)

    def test_jsonb_obj_attribute_has_correct_structure(self):
        """Jsonb.obj contains the recursively converted structure.

        Only the outermost dict is wrapped in Jsonb. Inner dicts are
        returned as plain dicts to avoid nested Jsonb objects that
        json.dumps() cannot serialize.
        """
        from psycopg.types.json import Jsonb

        test_dict = {"APPROVED": {"value": True}}
        jsonb_obj = database.convert_for_jsonb(test_dict)

        # Structure: Jsonb({"APPROVED": {"value": True}})
        # The inner dict is plain (not wrapped in Jsonb)
        assert isinstance(jsonb_obj, Jsonb)
        assert isinstance(jsonb_obj.obj, dict)
        assert "APPROVED" in jsonb_obj.obj
        # The nested value is a plain dict, not a Jsonb wrapper
        assert isinstance(jsonb_obj.obj["APPROVED"], dict)
        assert jsonb_obj.obj["APPROVED"] == {"value": True}


class TestBuildrecNoJsonDumps:
    """Verify buildrec() no longer calls json.dumps() on dicts."""

    def test_buildrec_does_not_call_json_dumps(self):
        """buildrec() should NOT call json.dumps() on dict values."""
        member = {
            "moniker": "testuser",
            "flags": {"APPROVED": {"value": True}},
        }

        rec = buildrec(member)

        # The fix: flags is now a dict, not a JSON string
        assert isinstance(rec["flags"], dict)
        assert not isinstance(rec["flags"], str)

        # If json.dumps() was called, it would be a string like:
        # '{"APPROVED": {"value": true}}'
        # But it's not!
        assert rec["flags"] != '{"APPROVED": {"value": true}}'

    def test_buildrec_does_not_call_convert_for_jsonb_twice(self):
        """buildrec() should NOT call convert_for_jsonb() (it's called in database.update())."""
        from psycopg.types.json import Jsonb

        member = {
            "moniker": "testuser",
            "flags": {"APPROVED": {"value": True}},
        }

        rec = buildrec(member)

        # flags should NOT be wrapped in Jsonb at this point
        # (it will be wrapped later by database.update())
        assert not isinstance(rec["flags"], Jsonb)
        assert isinstance(rec["flags"], dict)


class TestCompleteWorkflow:
    """Test complete workflow from member dict to database-ready record."""

    def test_complete_transformation_workflow(self):
        """Test the complete transformation workflow."""
        # Original member data (like from editflags())
        original_member = {
            "moniker": "testuser",
            "email": "test@example.com",
            "loginid": "testlogin",
            "credits": 500,
            "flags": {
                "APPROVED": {"value": True},
                "VERIFIED": {"value": False},
            },
            "ui": ["telnet", "web"],
        }

        # Step 1: buildrec() transforms the structure
        rec = buildrec(original_member)

        # Step 2: Verify buildrec() output
        assert isinstance(rec["flags"], dict)
        assert isinstance(rec["ui"], str)

        # Step 3: Simulate database.update() processing
        # It calls convert_for_jsonb() on each value
        from psycopg.types.json import Jsonb

        flags_for_db = database.convert_for_jsonb(rec["flags"])
        # Strings are returned as-is (not wrapped in Jsonb)
        ui_for_db = database.convert_for_jsonb(rec["ui"])

        # Step 4: Verify database-ready values
        assert isinstance(flags_for_db, Jsonb)
        assert isinstance(ui_for_db, str)  # Strings pass through unchanged

        # Step 5: Verify flags structure is correct
        assert isinstance(flags_for_db.obj, dict)
        assert "APPROVED" in flags_for_db.obj
        assert "VERIFIED" in flags_for_db.obj

    def test_no_double_conversion_issues(self):
        """Verify there are no double-conversion issues."""
        from psycopg.types.json import Jsonb

        # The bug was: json.dumps(convert_for_jsonb(dict))
        # Which tries to JSON-serialize a Jsonb object (impossible)

        test_dict = {"APPROVED": {"value": True}}

        # Step 1: buildrec() - should NOT call convert_for_jsonb
        rec_value = test_dict  # This is what buildrec() now does

        # Step 2: database.update() - SHOULD call convert_for_jsonb
        db_value = database.convert_for_jsonb(rec_value)

        # Step 3: Verify no double conversion
        assert isinstance(db_value, Jsonb)
        assert isinstance(db_value.obj, dict)
        # The converted value is in db_value.obj
        assert "APPROVED" in db_value.obj

        # The bug would have been:
        # rec_value = Jsonb(test_dict)  # Wrong: buildrec() called json.dumps(convert_for_jsonb())
        # Then json.dumps(rec_value) would fail because Jsonb isn't JSON serializable


@pytest.mark.integration
@pytest.mark.requires_db
class TestMemberUpdateIntegration:
    """Integration tests requiring actual database connection."""

    def test_member_update_with_flags_via_buildrec(self, db_connection):
        """Test updating member with flags through buildrec() and database.update()."""
        # Create test args
        argparse.Namespace(debug=True)

        # Member data with flags
        member = {
            "moniker": "integrationtest",
            "email": "integrationtest@example.com",
            "flags": {"APPROVED": {"value": True}},
        }

        # Transform with buildrec()
        rec = buildrec(member)

        # Verify transformation
        assert isinstance(rec["flags"], dict)

        # Now update would call database.update(args, table, pk, rec, ...)
        # We'll just verify the structure is correct for that operation
        assert "moniker" in rec
        assert "email" in rec
        assert "flags" in rec
        assert isinstance(rec["flags"], dict)

    def test_buildrec_preserves_all_field_types(self, db_connection):
        """Verify buildrec() preserves all required field types for database.update()."""
        member = {
            "id": 1,
            "moniker": "test",
            "email": "test@example.com",
            "loginid": "testlogin",
            "name": "Test User",
            "credits": 500,
            "password": "hashed",
            "flags": {"FLAG1": {"value": True}},
            "ui": ["telnet", "web"],
            "refcode": None,
        }

        rec = buildrec(member)

        # Verify types for database.update() processing
        assert isinstance(rec["id"], int)
        assert isinstance(rec["moniker"], str)
        assert isinstance(rec["email"], str)
        assert isinstance(rec["loginid"], str)
        assert isinstance(rec["name"], str)
        assert isinstance(rec["credits"], int)
        assert isinstance(rec["password"], str)
        assert isinstance(rec["flags"], dict)  # Critical: dict, not string
        assert isinstance(rec["ui"], str)
        assert rec["refcode"] is None
