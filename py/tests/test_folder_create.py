"""Tests for bbsengine6.folder.create() function."""

import os
import argparse

import pytest

from bbsengine6 import database, folder


@pytest.fixture(scope="module")
def test_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": os.environ.get("BBSENGINE6_TEST_DBNAME", "zoid6"),
        "databasehost": os.environ.get("BBSENGINE6_TEST_DBHOST", "/var/run/postgresql"),
        "databaseport": int(os.environ.get("BBSENGINE6_TEST_DBPORT", "5432")),
        "databaseuser": os.environ.get("BBSENGINE6_TEST_DBUSER", "opencode"),
        "databasepassword": os.environ.get("BBSENGINE6_TEST_DBPASS"),
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


@pytest.fixture(scope="module")
def test_pool(test_args):
    pool = database.getpool(test_args, dbname=test_args.databasename)
    test_args.pool = pool

    with database.connect(test_args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            cur.execute("create schema if not exists engine")
        conn.commit()

        with database.cursor(conn) as cur:
            cur.execute("""
                create table if not exists engine.__folder (
                    path text unique not null primary key,
                    title text,
                    intro text,
                    parent text,
                    createdbyid bigint,
                    datecreated timestamptz
                )
            """)
        conn.commit()

    yield pool
    pool.close()


@pytest.fixture
def db_conn(test_args, test_pool):
    conn = test_pool.getconn()
    conn.autocommit = False
    yield conn
    conn.rollback()
    test_pool.putconn(conn)


@pytest.fixture(scope="function", autouse=True)
def clean_test_folders(db_conn):
    yield
    try:
        with database.cursor(db_conn) as cur:
            cur.execute("delete from engine.__folder where path like 'top.foldercreatetest%';")
        db_conn.commit()
    except Exception:
        pass


class TestFolderCreate:
    """Test folder.create() function."""

    def test_create_returns_true_on_success(self, test_args, test_pool, db_conn):
        """Test that create returns True when folder is created."""
        f = {
            "path": folder.buildpath(test_args, "top.foldercreatetest.new"),
            "title": "New Folder",
            "intro": "Test intro",
        }
        result = folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()
        assert result is True

    def test_create_inserts_into_database(self, test_args, test_pool, db_conn):
        """Test that create actually inserts the folder into the database."""
        f = {
            "path": folder.buildpath(test_args, "top.foldercreatetest.inserted"),
            "title": "Inserted Folder",
            "intro": "Test intro",
        }
        folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()

        with database.cursor(db_conn) as cur:
            cur.execute(
                "select path, title, intro from engine.__folder where path = %s",
                (f["path"],),
            )
            row = cur.fetchone()
        assert row is not None
        assert row["path"] == f["path"]
        assert row["title"] == "Inserted Folder"

    def test_create_returns_false_if_exists(self, test_args, test_pool, db_conn):
        """Test that create returns False if folder already exists."""
        f = {
            "path": folder.buildpath(test_args, "top.foldercreatetest.exists"),
            "title": "Exists",
        }
        folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()

        result = folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()
        assert result is False

    def test_create_validates_path(self, test_args, test_pool, db_conn):
        """Test that create rejects invalid paths."""
        f = {
            "path": "invalid path with spaces",
            "title": "Bad Path",
        }
        result = folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()
        assert result is False

    def test_create_sets_metadata(self, test_args, test_pool, db_conn):
        """Test that create sets datecreated and createdbymoniker."""
        f = {
            "path": folder.buildpath(test_args, "top.foldercreatetest.meta"),
            "title": "Metadata Test",
        }
        folder.create(test_args, f, cur=db_conn.cursor())
        db_conn.commit()

        with database.cursor(db_conn) as cur:
            cur.execute(
                "select path, datecreated, createdbymoniker from engine.__folder where path = %s",
                (f["path"],),
            )
            row = cur.fetchone()
        assert row is not None
        assert row["datecreated"] is not None
