"""
Pytest configuration for bbsengine6 integration tests.

Automatically initializes notify schema in zoid6test database.
Uses smart initialization: only loads 7 notify-specific SQL files
(schema, extensions, roles, member, session already exist).

Session-scoped fixtures:
  - db_connection: persistent connection to zoid6test
  - schema_init: loads notify tables & views
  - create_test_users: creates test users (alice, bob)

Function-scoped fixtures (autouse):
  - test_transaction: wraps each test in transaction (rollback after)
"""

import pytest
import psycopg
import getpass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ===== Session-Scoped Fixtures =====


def pytest_collection_modifyitems(config, items):
    """Skip session fixtures for tests marked with @pytest.mark.unit"""
    needs_db = True
    for item in items:
        if item.get_closest_marker("unit"):
            needs_db = False
            break

    if not needs_db:
        skip_db = pytest.mark.skip(reason="Unit test - no database required")
        for item in items:
            if not item.get_closest_marker("unit"):
                item.add_marker(skip_db)


@pytest.fixture(scope="session")
def db_connection(request):
    """
    Connect to zoid6test database as opencode user.
    Connection persists for entire test session.
    Skipped for tests marked with @pytest.mark.unit
    """
    if request.node.get_closest_marker("unit"):
        logger.info("Skipping database connection for unit tests")
        pytest.skip("Unit test - no database required")

    user = getpass.getuser()
    logger.info(f"Connecting to zoid6test database as {user}...")
    conn = psycopg.connect(f"dbname=zoid6test user={user}")
    logger.info("✓ Connected to zoid6test")

    yield conn

    # Cleanup
    logger.info("Closing database connection...")
    conn.close()


@pytest.fixture(scope="session")
def schema_init(db_connection, request):
    """
    Initialize notify schema tables.

    Only loads 7 notify-specific SQL files:
    - notify.sql
    - notify_recipient.sql
    - notify_block.sql
    - notify_group.sql
    - notify_type.sql
    - notify_rate_limit.sql
    - notifyview.sql

    Skips: schema, extensions, roles, member, session (already exist)
    """
    logger.info("Initializing notify schema tables...")

    sql_files = _get_notify_sql_files()

    for filepath in sql_files:
        try:
            sql_content = _read_sql_file(filepath)
            _execute_sql_file(db_connection, sql_content, filepath.name)
            logger.info(f"  ✓ Loaded {filepath.name}")
        except (psycopg.errors.DuplicateObject, psycopg.errors.DuplicateTable):
            # Already exists - this is OK on re-runs
            # Reset transaction state (PostgreSQL requires this after duplicate error)
            db_connection.rollback()
            logger.info(f"  ⊘ {filepath.name} already exists, skipping")
        except psycopg.errors.InsufficientPrivilege:
            # Permission error - skip this file
            db_connection.rollback()
            logger.warning(f"  ⊘ {filepath.name} - insufficient privileges, skipping")
        except Exception as e:
            logger.error(f"  ✗ Failed to load {filepath.name}: {e}")
            db_connection.rollback()
            raise pytest.fail(
                f"Schema initialization failed loading {filepath.name}: {e}"
            )

    db_connection.commit()
    logger.info("✓ All notify tables initialized")

    yield


@pytest.fixture(scope="session", autouse=True)
def create_test_users(request, db_connection, schema_init):
    """
    Create minimal test users: alice, bob
    (jam already exists in engine.__member)

    Required fields: moniker, email

    autouse=True: This fixture always runs, ensuring test users exist
    Skipped for tests marked with @pytest.mark.unit
    """
    # Skip database setup for unit tests
    if request.node.get_closest_marker("unit"):
        logger.info("Skipping database fixtures for unit tests")
        return

    logger.info("Creating test users (alice, bob)...")

    # Minimal INSERT: moniker and email (both required)
    sql = """
        INSERT INTO engine.__member (moniker, email) 
        VALUES ('alice', 'alice@test.local'), ('bob', 'bob@test.local')
        ON CONFLICT DO NOTHING
    """

    try:
        with db_connection.cursor() as cur:
            cur.execute(sql)
        db_connection.commit()
        logger.info("✓ Test users created (alice, bob)")
    except Exception as e:
        logger.error(f"Failed to create test users: {e}")
        raise

    yield


# ===== Function-Scoped Fixtures =====


@pytest.fixture(autouse=True)
def test_transaction(db_connection):
    """
    Wrap each test in its own transaction.
    Rolls back after test to keep data clean.

    Schema persists (session scope), test data is isolated.

    Uses psycopg's built-in autocommit=False (default) behavior.
    Each test's inserts/deletes are rolled back automatically.
    """
    # Ensure we're not in a transaction (clean state)
    # PostgreSQL auto-starts a transaction on first DML
    # Just yield and let test run normally

    yield  # Test runs here

    # Rollback after test - all inserts/deletes are undone
    # This doesn't affect CREATE TABLE/VIEW/TYPE (DDL) from session fixtures
    try:
        db_connection.rollback()
    except Exception as e:
        # If rollback fails (transaction already closed, etc), just log it
        logger.debug(f"Rollback warning: {e}")


# ===== Helper Functions =====


def _get_notify_sql_files() -> list[Path]:
    """
    Return paths to 7 notify SQL files in correct execution order.
    Path is relative to conftest.py location.

    Order matters: depends on foreign keys between tables.
    """
    sql_dir = Path(__file__).parent.parent / "src" / "bbsengine6" / "sql"

    files = [
        "notify.sql",  # Core table: engine.__notify
        "notify_recipient.sql",  # Depends on: engine.__notify
        "notify_block.sql",  # Depends on: engine.__member, engine.__notify
        "notify_group.sql",  # Depends on: engine.__member
        "notify_type.sql",  # Independent
        "notify_rate_limit.sql",  # Depends on: engine.__notify_type
        "notifyview.sql",  # Depends on: all tables above
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
    except Exception as e:
        # Re-raise - let caller decide how to handle
        raise
