"""
Pytest configuration for bbsengine6 tests.

Behavior:
  - Tests marked with @pytest.mark.unit run with NO database connection.
  - All other tests use the live `zoid6` database (must be reachable as the
    current OS user), loading message/bank schema and creating dynamic
    test users under the OS username.

Session-scoped fixtures:
  - db_connection: persistent connection to zoid6
  - schema_init: loads message + bank tables
  - create_test_users: creates test_{user}_1..3 with approved=TRUE

Function-scoped fixtures (autouse, integration only):
  - test_transaction: rolls back after each test
"""

import atexit
import os

os.environ["BBSENGINE6_DBNAME"] = "zoid6"

import pytest
import psycopg
import getpass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_pools_to_close = []


def _close_test_pools():
    global _pools_to_close
    for pool in _pools_to_close[:]:
        try:
            pool.closeall()
        except Exception:
            pass
    _pools_to_close.clear()


atexit.register(_close_test_pools)


# ===== Collection-time decision: does this session need a DB? =====


def pytest_collection_modifyitems(config, items):
    """
    Decide once per session whether any collected test needs the database.
    A test needs a DB unless it is marked @pytest.mark.unit.

    The result is stored on config so that session-scoped DB fixtures can
    skip cleanly when the entire run is unit-only (avoids the "first test
    decides for everyone" pitfall of session-scoped skip fixtures).
    """
    needs_db = any(
        not item.get_closest_marker("unit") for item in items
    )
    config._bbsengine6_session_needs_db = needs_db
    if not needs_db:
        logger.info("Session is unit-only: all DB fixtures will skip")


# ===== Session-Scoped Fixtures =====


def _session_needs_db(request) -> bool:
    """True if any test in this session is not marked @pytest.mark.unit."""
    return bool(getattr(request.config, "_bbsengine6_session_needs_db", True))


@pytest.fixture(scope="session")
def db_connection(request):
    """
    Connect to zoid6 database as the current OS user. Skipped for unit-only
    sessions.
    """
    if not _session_needs_db(request):
        pytest.skip("unit-only session: no database required")

    user = getpass.getuser()
    logger.info(f"Connecting to zoid6 database as {user}...")
    conn = psycopg.connect(f"dbname=zoid6 user={user}")
    logger.info("✓ Connected to zoid6")

    yield conn

    logger.info("Closing database connection...")
    conn.close()


@pytest.fixture(scope="session")
def pool(db_connection, schema_init, request):
    """
    Create a database connection pool for tests.

    Required for CONN_POOL_PATTERN in bbsengine6 modules.
    """
    from bbsengine6 import database

    pool_obj = database.getpool(None, dbname="zoid6", user=getpass.getuser())

    def close_pool():
        try:
            database.reset_pool_cache()
        except Exception:
            pass

    request.addfinalizer(close_pool)

    return pool_obj


@pytest.fixture(scope="session")
def schema_init(db_connection, request):
    """
    Initialize message and bank schema tables.

    Only loads message-specific SQL files:
    - message.sql
    - message_groups.sql
    - messageview.sql
    - channel.sql (Channel config: engine.__channel, engine.__channel_announcer)
    - invite.sql (Generic invite code system: engine.__invite, engine.invite)

    Also loads bank schema:
    - bank_schema.sql
    - bank_account.sql
    - bank_account_view.sql
    - bank_transaction.sql
    - bank_transaction_view.sql
    - bank_transfer.sql
    - bank_transfer_view.sql

    Skips: schema, extensions, roles, member, session (already exist)
    """
    logger.info("Initializing message schema tables...")

    # Ensure messageview.sql's predicates can reference engine.__member.approved.
    # member.sql's CREATE TABLE IF NOT EXISTS will not retro-add columns to a
    # pre-existing table; this ALTER is idempotent and safe on fresh DBs.
    with db_connection.cursor() as cur:
        cur.execute(
            "ALTER TABLE engine.__member "
            "ADD COLUMN IF NOT EXISTS approved boolean NOT NULL DEFAULT false"
        )
    db_connection.commit()

    sql_files = _get_message_sql_files()

    for filepath in sql_files:
        try:
            sql_content = _read_sql_file(filepath)
            _execute_sql_file(db_connection, sql_content, filepath.name)
            logger.info(f"  ✓ Loaded {filepath.name}")
        except (psycopg.errors.DuplicateObject, psycopg.errors.DuplicateTable):
            db_connection.rollback()
            logger.info(f"  ⊘ {filepath.name} already exists, skipping")
        except psycopg.errors.InsufficientPrivilege:
            db_connection.rollback()
            logger.warning(f"  ⊘ {filepath.name} - insufficient privileges, skipping")
        except psycopg.errors.DependentObjectsStillExist:
            db_connection.rollback()
            logger.warning(f"  ⊘ {filepath.name} - dependent objects, skipping (can only run on clean schema)")
        except Exception as e:
            logger.error(f"  ✗ Failed to load {filepath.name}: {e}")
            db_connection.rollback()
            raise pytest.fail(
                f"Schema initialization failed loading {filepath.name}: {e}"
            )

    db_connection.commit()
    logger.info("✓ All message tables initialized")

    logger.info("Initializing bank schema tables...")
    _load_bank_schema(db_connection)

    yield


def _get_bank_sql_files() -> list[Path]:
    """Return paths to bank SQL files in correct execution order."""
    sql_dir = Path(__file__).parent.parent / "src" / "bbsengine6" / "sql"

    files = [
        "bank_schema.sql",
        "bank_account.sql",
        "bank_account_view.sql",
        "bank_transaction.sql",
        "bank_transaction_view.sql",
        "bank_transfer.sql",
        "bank_transfer_view.sql",
    ]

    paths = [sql_dir / f for f in files]

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {path}")

    return paths


def _load_bank_schema(db_connection):
    """Load bank schema SQL files."""
    sql_files = _get_bank_sql_files()

    for filepath in sql_files:
        try:
            sql_content = _read_sql_file(filepath)
            _execute_sql_file(db_connection, sql_content, filepath.name)
            logger.info(f"  ✓ Loaded {filepath.name}")
        except (psycopg.errors.DuplicateObject, psycopg.errors.DuplicateTable):
            db_connection.rollback()
            logger.info(f"  ⊘ {filepath.name} already exists, skipping")
        except psycopg.errors.InsufficientPrivilege:
            db_connection.rollback()
            logger.warning(f"  ⊘ {filepath.name} - insufficient privileges, skipping")
        except Exception as e:
            logger.error(f"Failed to load {filepath.name}: {e}")
            db_connection.rollback()
            raise pytest.fail(f"Schema initialization failed loading {filepath.name}: {e}")

    db_connection.commit()


@pytest.fixture(scope="session")
def create_test_users(request, db_connection, schema_init):
    """
    Create minimal test users dynamically based on OS username.
    Uses test_{user}_1, test_{user}_2, test_{user}_3 pattern.

    Required fields: moniker, email, approved=TRUE (so messageview includes them).

    Tests that need these users list `create_test_users` or `test_users` as a
    fixture parameter. The fixture is no longer autouse, so unit-marked tests
    do not trigger schema initialization.
    """
    user = getpass.getuser()
    test_users = [
        (f"test_{user}_1", f"test_{user}_1@test.local"),
        (f"test_{user}_2", f"test_{user}_2@test.local"),
        (f"test_{user}_3", f"test_{user}_3@test.local"),
    ]

    logger.info(f"Creating dynamic test users for {user}...")

    sql = (
        "INSERT INTO engine.__member (moniker, email, approved) "
        "VALUES (%s, %s, TRUE) "
        "ON CONFLICT (moniker) DO UPDATE SET approved = TRUE"
    )

    try:
        with db_connection.cursor() as cur:
            for moniker, email in test_users:
                cur.execute(sql, (moniker, email))
        db_connection.commit()
        logger.info(f"✓ Test users created: {[u[0] for u in test_users]}")
    except psycopg.errors.InsufficientPrivilege:
        db_connection.rollback()
        logger.warning("⊘ Insufficient privileges to create test users, skipping")
    except Exception as e:
        logger.error(f"Failed to create test users: {e}")
        raise

    yield


@pytest.fixture
def test_users():
    """Return the list of dynamic test user monikers."""
    user = getpass.getuser()
    return [f"test_{user}_1", f"test_{user}_2", f"test_{user}_3"]


# ===== Function-Scoped Fixtures =====


@pytest.fixture(autouse=True)
def test_create_test_users(request):
    """
    Populate test users (test_{user}_1..3) for any non-unit test.

    Skipped for tests marked with @pytest.mark.unit. Made autouse so that
    tests like test_member_verify_found.py which exercise the live
    members table get the test data they need without each test having
    to declare ``create_test_users`` explicitly.

    NOTE: create_test_users is fetched lazily via request.getfixturevalue
    so unit-only sessions don't cascade the DB fixture's skip.
    """
    if request.node.get_closest_marker("unit"):
        yield
        return

    request.getfixturevalue("create_test_users")
    yield


@pytest.fixture(autouse=True)
def test_transaction(request):
    """
    Wrap each non-unit test in its own transaction.
    Rolls back after the test to keep data clean.

    Skipped for tests marked with @pytest.mark.unit (so unit tests never
    trigger DB session fixtures).

    NOTE: db_connection is fetched lazily via request.getfixturevalue so
    unit-only sessions don't cascade the DB fixture's skip to this autouse
    fixture.
    """
    if request.node.get_closest_marker("unit"):
        yield
        return

    db_connection = request.getfixturevalue("db_connection")

    yield  # Test runs here

    try:
        if db_connection and hasattr(db_connection, "rollback"):
            db_connection.rollback()
    except Exception:
        pass


# ===== Helper Functions =====


def _get_message_sql_files() -> list[Path]:
    """
    Return paths to message SQL files in correct execution order.
    Path is relative to conftest.py location.

    Order matters: depends on foreign keys between tables.
    """
    sql_dir = Path(__file__).parent.parent / "src" / "bbsengine6" / "sql"

    files = [
        "message.sql",  # Core message tables
        "message_groups.sql",  # Groups, blocking, rate limiting, types
        "messageview.sql",  # Views
        "channel.sql",  # Channel config
        "invite.sql",  # Invite codes
    ]

    paths = [sql_dir / f for f in files]

    # Verify all files exist
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {path}")

    return paths


def _read_sql_file(filepath: Path) -> str:
    r"""
    Read SQL file and remove psql metacommands.

    Lines starting with backslash (\set, \echo, \i) are psql-only
    metacommands and should be removed before executing with Python.
    """
    with open(filepath) as f:
        lines = f.readlines()

    # Keep only actual SQL (remove lines starting with \)
    cleaned = [
        line for line in lines if line.strip() and not line.strip().startswith("\\")
    ]

    return "".join(cleaned)


def _execute_sql_file(conn, sql_content: str, filename: str) -> None:
    """
    Execute SQL content.

    On "already exists" error: raise (caller handles with logging)
    On other errors: raise immediately
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
    except Exception:
        # Re-raise - let caller decide how to handle
        raise
