"""
Unit tests for bbsengine6.member.buildrec() function.

Tests verify that:
1. Dict values remain as dicts (not JSON strings)
2. Non-dict values pass through unchanged
3. Excluded fields are skipped
4. UI lists are converted to comma-separated strings
5. Overall structure is correct for database operations
"""

import pytest
from bbsengine6.member import buildrec


class TestBuildrecBasicFunctionality:
    """Test basic buildrec() behavior."""

    def test_buildrec_dict_values_stay_as_dicts(self):
        """Dict values should remain as dicts after buildrec(), not JSON strings."""
        member = {
            "moniker": "testuser",
            "flags": {"APPROVED": {"value": True}, "VERIFIED": {"value": False}},
            "name": "Test User",
        }
        result = buildrec(member)

        # After fix: flags stays as dict
        assert isinstance(result["flags"], dict), "flags should remain a dict"
        assert result["flags"] == {
            "APPROVED": {"value": True},
            "VERIFIED": {"value": False},
        }

    def test_buildrec_nested_dict_values(self):
        """Nested dicts should also remain as dicts."""
        member = {
            "moniker": "testuser",
            "attrs": {"nested": {"deep": {"value": "test"}}},
        }
        # Note: 'attrs' is in the exclude list, so it won't be in result
        # But test a different dict field
        member["custom_dict"] = {"nested": {"deep": {"value": "test"}}}

        result = buildrec(member)

        assert isinstance(result["custom_dict"], dict)
        assert result["custom_dict"]["nested"]["deep"]["value"] == "test"

    def test_buildrec_string_values_unchanged(self):
        """String values should pass through unchanged."""
        member = {
            "moniker": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        }
        result = buildrec(member)

        assert result["moniker"] == "testuser"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"

    def test_buildrec_numeric_values_unchanged(self):
        """Numeric values should pass through unchanged."""
        member = {
            "id": 123,
            "credits": 500,
            "loginid": "user123",
        }
        result = buildrec(member)

        assert result["id"] == 123
        assert result["credits"] == 500


class TestBuildrecExcludedFields:
    """Test that excluded fields are properly skipped."""

    def test_buildrec_excludes_epoch_fields(self):
        """Epoch timestamp fields should be excluded."""
        member = {
            "moniker": "testuser",
            "datecreatedepoch": 1234567890,
            "dateapprovedepoch": 1234567900,
            "dateupdatedepoch": 1234567910,
            "lastloginepoch": 1234567920,
        }
        result = buildrec(member)

        assert "datecreatedepoch" not in result
        assert "dateapprovedepoch" not in result
        assert "dateupdatedepoch" not in result
        assert "lastloginepoch" not in result

    def test_buildrec_excludes_attrs_field(self):
        """The 'attrs' field should be excluded."""
        member = {
            "moniker": "testuser",
            "attrs": {"some": "data"},
        }
        result = buildrec(member)

        assert "attrs" not in result

    def test_buildrec_keeps_non_excluded_fields(self):
        """Non-excluded fields should be included."""
        member = {
            "moniker": "testuser",
            "email": "test@example.com",
            "loginid": "login123",
        }
        result = buildrec(member)

        assert "moniker" in result
        assert "email" in result
        assert "loginid" in result


class TestBuildrecUIHandling:
    """Test special handling of UI field."""

    def test_buildrec_ui_list_to_string(self):
        """UI list should be converted to comma-separated string."""
        member = {
            "moniker": "testuser",
            "ui": ["telnet", "web", "ssh"],
        }
        result = buildrec(member)

        assert isinstance(result["ui"], str)
        assert result["ui"] == "telnet, web, ssh"

    def test_buildrec_ui_empty_list(self):
        """Empty UI list should result in empty string."""
        member = {
            "moniker": "testuser",
            "ui": [],
        }
        result = buildrec(member)

        assert isinstance(result["ui"], str)
        assert result["ui"] == ""

    def test_buildrec_ui_single_item(self):
        """Single-item UI list should be string without comma."""
        member = {
            "moniker": "testuser",
            "ui": ["telnet"],
        }
        result = buildrec(member)

        assert isinstance(result["ui"], str)
        assert result["ui"] == "telnet"


class TestBuildrecOutputStructure:
    """Test overall output structure and behavior."""

    def test_buildrec_complete_member_record(self):
        """Test with complete member record matching actual use case."""
        member = {
            "id": 1,
            "moniker": "testuser",
            "loginid": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "credits": 500,
            "password": "hashed_password",
            "flags": {
                "APPROVED": {"value": True},
                "EMAILVERIFIED": {"value": False},
            },
            "ui": ["telnet", "web"],
            "datecreated": "2023-01-01T00:00:00",
            "datecreatedepoch": 1234567890,  # Should be excluded
            "attrs": {"some": "data"},  # Should be excluded
        }

        result = buildrec(member)

        # Verify all included fields
        assert result["id"] == 1
        assert result["moniker"] == "testuser"
        assert result["loginid"] == "user123"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["credits"] == 500
        assert result["password"] == "hashed_password"

        # Verify flags stayed as dict
        assert isinstance(result["flags"], dict)
        assert result["flags"]["APPROVED"]["value"] is True

        # Verify UI was converted to string
        assert isinstance(result["ui"], str)
        assert result["ui"] == "telnet, web"

        # Verify excluded fields are absent
        assert "datecreatedepoch" not in result
        assert "attrs" not in result

    def test_buildrec_with_none_values(self):
        """None values should pass through unchanged."""
        member = {
            "moniker": "testuser",
            "refcode": None,
            "flags": None,
        }
        result = buildrec(member)

        assert result["moniker"] == "testuser"
        assert result["refcode"] is None
        # flags is None (not a dict), so doesn't go through dict handler
        assert result["flags"] is None

    def test_buildrec_does_not_modify_input(self):
        """buildrec() should not modify the input member dict."""
        original_member = {
            "moniker": "testuser",
            "flags": {"APPROVED": {"value": True}},
            "ui": ["telnet", "web"],
        }
        member_copy = original_member.copy()

        result = buildrec(original_member)

        # Input should not be modified
        assert original_member == member_copy
        # Output should have modified values
        assert isinstance(result["flags"], dict)
        assert isinstance(result["ui"], str)


class TestBuildrecTypeChecking:
    """Test strict type checking (type(v) is dict, not isinstance)."""

    def test_buildrec_uses_strict_type_check_for_dict(self):
        """Should use 'type(v) is dict' not isinstance() for dict check."""
        # This tests the implementation detail, but it's important
        # because subclasses of dict might behave differently

        class CustomDict(dict):
            pass

        member = {
            "moniker": "testuser",
            "custom_dict": CustomDict({"key": "value"}),
        }
        result = buildrec(member)

        # With strict type check, CustomDict won't be handled as dict
        # It will fall through to the else clause
        assert "custom_dict" in result
        # The CustomDict instance should be passed through as-is
        assert result["custom_dict"] == {"key": "value"}

    def test_buildrec_strict_ui_list_check(self):
        """UI field must be type list, not other iterables."""
        member = {
            "moniker": "testuser",
            "ui": ("telnet", "web"),  # tuple, not list
        }
        result = buildrec(member)

        # With strict type check, tuple won't be converted
        # It will pass through as-is
        assert result["ui"] == ("telnet", "web")


class TestBuildrecEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_buildrec_empty_dict_field(self):
        """Empty dict field should be preserved as empty dict."""
        member = {
            "moniker": "testuser",
            "flags": {},
        }
        result = buildrec(member)

        assert result["flags"] == {}
        assert isinstance(result["flags"], dict)

    def test_buildrec_dict_with_complex_values(self):
        """Dict with complex nested values should be preserved."""
        member = {
            "moniker": "testuser",
            "flags": {
                "APPROVED": {"value": True, "timestamp": 1234567890},
                "VERIFIED": {
                    "value": False,
                    "reason": "Not verified",
                    "nested": {"data": "test"},
                },
            },
        }
        result = buildrec(member)

        assert isinstance(result["flags"], dict)
        assert result["flags"]["APPROVED"]["timestamp"] == 1234567890
        assert result["flags"]["VERIFIED"]["nested"]["data"] == "test"

    def test_buildrec_preserves_dict_order(self):
        """Dict field should preserve key order (Python 3.7+)."""
        from collections import OrderedDict

        member = {
            "moniker": "testuser",
            "flags": {"Z": {"value": 1}, "A": {"value": 2}, "M": {"value": 3}},
        }
        result = buildrec(member)

        # Should preserve insertion order
        keys = list(result["flags"].keys())
        assert keys == ["Z", "A", "M"]
