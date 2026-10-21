"""Message groups against zoid6test: create, membership, last-leave, delete.

Runs only when the zoid6test message schema is present. Seeds the members it
uses and removes every row it creates, so zoid6test is left as it was found.
"""

import psycopg
import pytest

from bbsengine6.message import lib as message_lib

DB = "zoid6test"
GROUP = "table:integration-jam"
MEMBERS = ("gina", "hank")
TAG = "@integration.test"


def _connect():
    return psycopg.connect(f"host=/var/run/postgresql port=5432 dbname={DB} user=opencode")


def _schema_present() -> bool:
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("select to_regclass('engine.__message_group') is not null")
            return bool(cur.fetchone()[0])
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_db,
    pytest.mark.skipif(not _schema_present(), reason="zoid6test message schema not present"),
]


@pytest.fixture
def seeded():
    with _connect() as conn, conn.cursor() as cur:
        for m in MEMBERS:
            cur.execute(
                "INSERT INTO engine.__member (moniker, email, approved) "
                "VALUES (%s, %s, true) ON CONFLICT (moniker) DO NOTHING",
                (m, m + TAG),
            )
        conn.commit()
    yield
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM engine.__message_group WHERE name = %s", (GROUP,))
        cur.execute(
            "DELETE FROM engine.__member WHERE moniker = ANY(%s) AND email LIKE %s",
            (list(MEMBERS), "%" + TAG),
        )
        conn.commit()




def test_group_membership_lifecycle(seeded):
    from bbsengine6.message import service as svc

    svc.ensure_message_group(GROUP, database=DB)
    assert svc.group_member_monikers(GROUP, database=DB) == []

    svc.group_member_add(GROUP, "gina", database=DB)
    svc.group_member_add(GROUP, "hank", database=DB)
    assert sorted(svc.group_member_monikers(GROUP, database=DB)) == ["gina", "hank"]

    svc.group_member_remove(GROUP, "gina", database=DB)
    assert svc.group_member_monikers(GROUP, database=DB) == ["hank"]

    svc.group_member_remove(GROUP, "hank", database=DB)
    # Last member leaves: the group itself is deleted.
    assert svc.group_member_monikers(GROUP, database=DB) == []
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM engine.__message_group WHERE name = %s", (GROUP,))
        assert cur.fetchone()[0] == 0


def test_group_delete_removes_group_and_members(seeded):
    from bbsengine6.message import service as svc

    svc.group_member_add(GROUP, "gina", database=DB)
    assert svc.group_delete(GROUP, database=DB) is True
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM engine.__message_group WHERE name = %s", (GROUP,))
        assert cur.fetchone()[0] == 0


def test_named_source_registration_roundtrip(seeded):
    from bbsengine6.message import service as svc

    source = "casino.dealer:integration-jam"
    svc.register_named_source(source, GROUP, database=DB)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM engine.__message_source WHERE source = %s", (source,))
        assert cur.fetchone()[0] == 1
    svc.unregister_named_source(source, database=DB)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM engine.__message_source WHERE source = %s", (source,))
        assert cur.fetchone()[0] == 0
