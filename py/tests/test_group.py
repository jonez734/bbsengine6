"""
Unit tests for bbsengine6.group module.

Tests group management operations: validation, existence checks, and member retrieval.
Uses CONN_POOL_PATTERN for database connections.
"""

import pytest

from bbsengine6 import group


class TestValidateName:
    """Test group name validation."""

    def test_valid_group_names(self):
        group.validate_name("ops")
        group.validate_name("admins")
        group.validate_name("team-alpha")
        group.validate_name("DevOps_Team")
        group.validate_name("a")

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="must be non-empty"):
            group.validate_name("")
        with pytest.raises(ValueError, match="must be non-empty"):
            group.validate_name(None)

    def test_starts_with_at_raises(self):
        with pytest.raises(ValueError, match="cannot start with '@'"):
            group.validate_name("@ops")

    def test_contains_space_raises(self):
        with pytest.raises(ValueError, match="cannot contain spaces"):
            group.validate_name("my group")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="exceeds 100 characters"):
            group.validate_name("A" * 101)

    def test_non_printable_raises(self):
        with pytest.raises(ValueError, match="non-printable character"):
            group.validate_name("ops\x00test")
        with pytest.raises(ValueError, match="non-printable character"):
            group.validate_name("ops\ntest")


class TestGroupExists:
    """Test group existence checking."""

    def test_exists_with_pool_creates_connection(self, pool):
        result = group.exists(None, "testgroup", pool=pool)
        assert isinstance(result, bool)

    def test_exists_with_conn_uses_provided_connection(self, pool, db_connection):
        result = group.exists(None, "testgroup", conn=db_connection, pool=pool)
        assert isinstance(result, bool)

    def test_exists_invalid_group_name(self):
        with pytest.raises(ValueError):
            group.exists(None, "")

    def test_exists_nonexistent_group(self, pool):
        result = group.exists(None, "nonexistent_group_xyz", pool=pool)
        assert result is False


class TestGroupExistsIntegration:
    """Integration tests for group.exists() with real database."""

    def test_exists_after_create(self, pool, db_connection, test_users):
        db_connection.rollback()
        test_group = "test_int_group"
        user1 = test_users[0]

        try:
            with db_connection.cursor() as cur:
                cur.execute(
                    "INSERT INTO engine.__notify_group (group_name, member_moniker) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (test_group, user1),
                )
            db_connection.commit()

            exists_before = group.exists(None, test_group, pool=pool)
            assert exists_before is True

            with db_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM engine.__notify_group WHERE group_name=%s",
                    (test_group,),
                )
            db_connection.commit()

            exists_after = group.exists(None, test_group, pool=pool)
            assert exists_after is False
        except Exception:
            db_connection.rollback()
            raise


class TestGetMembers:
    """Test group member retrieval."""

    def test_get_members_empty_group(self, pool):
        result = group.get_members(None, "nonexistent", pool=pool)
        assert result == []

    def test_get_members_with_conn(self, pool, db_connection):
        result = group.get_members(None, "test", conn=db_connection, pool=pool)
        assert isinstance(result, list)

    def test_get_members_invalid_name(self):
        with pytest.raises(ValueError):
            group.get_members(None, "")

    def test_get_members_circular_detection(self, pool):
        visited = {"group1", "group2"}
        with pytest.raises(ValueError, match="Circular group reference"):
            group.get_members(None, "group1", pool=pool, _visited=visited)


class TestGetMembersIntegration:
    """Integration tests for group.get_members() with real database."""

    def test_get_members_after_insert(self, pool, db_connection, test_users):
        db_connection.rollback()
        test_group = "test_members_group"
        user1, user2, user3 = test_users[0], test_users[1], test_users[2]

        try:
            with db_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM engine.__notify_group WHERE group_name=%s",
                    (test_group,),
                )
                cur.execute(
                    "INSERT INTO engine.__notify_group (group_name, member_moniker) VALUES "
                    "(%s, %s), (%s, %s), (%s, %s)",
                    (test_group, user1, test_group, user2, test_group, user3),
                )
            db_connection.commit()

            members = group.get_members(None, test_group, pool=pool)
            assert members is not None
            assert len(members) == 3
            assert set(members) == {user1, user2, user3}
        except Exception:
            db_connection.rollback()
            raise
        finally:
            with db_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM engine.__notify_group WHERE group_name=%s",
                    (test_group,),
                )
            db_connection.commit()

    def test_get_members_multiple_members(self, pool, db_connection, test_users):
        test_group = "multi_member_group"
        user1, user2, user3 = test_users[0], test_users[1], test_users[2]

        try:
            with db_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM engine.__notify_group WHERE group_name=%s",
                    (test_group,),
                )
                cur.execute(
                    "INSERT INTO engine.__notify_group (group_name, member_moniker) VALUES "
                    "(%s, %s), (%s, %s), (%s, %s)",
                    (test_group, user1, test_group, user2, test_group, user3),
                )
            db_connection.commit()

            members = group.get_members(None, test_group, pool=pool)
            assert members is not None
            assert len(members) == 3
            assert set(members) == {user1, user2, user3}
        except Exception:
            db_connection.rollback()
            raise
        finally:
            with db_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM engine.__notify_group WHERE group_name=%s",
                    (test_group,),
                )
            db_connection.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
