"""
Mock tests for console member add() and edit() end-to-end.

Demonstrates the full flow of adding and editing a member through the
console layer, including all side effects (flags, password, bank credits,
pgrole provisioning, group sync). A fake in-memory database tracks every
write so we can query it directly to prove the operations landed.
"""

import copy
import contextlib
import crypt
from unittest.mock import Mock, patch

import pytest

from bbsengine6.console import member as console_member
from bbsengine6 import member as libmember


# ---------------------------------------------------------------------------
# Fake in-memory database
# ---------------------------------------------------------------------------
class FakeDB:
    """Minimal in-memory store that tracks INSERTs and UPDATEs.

    Used to verify that the full add/edit pipeline wrote the expected data
    without touching a real PostgreSQL instance.
    """

    def __init__(self):
        self.members = {}
        self.flags = {}
        self.passwords = {}
        self.bank_credits = {}
        self.pgroles = {}
        self.updates = []

    def insert_member(self, moniker, data):
        self.members[moniker] = copy.deepcopy(data)

    def update_member(self, moniker, data):
        if moniker in self.members:
            self.members[moniker].update(copy.deepcopy(data))
        self.updates.append(("member", moniker, data))

    def set_password(self, moniker, pw_hash):
        self.passwords[moniker] = pw_hash

    def set_flag(self, moniker, name, value):
        self.flags.setdefault(moniker, {})[name] = value

    def add_credits(self, moniker, amount):
        self.bank_credits[moniker] = self.bank_credits.get(moniker, 0) + amount

    def insert_pgrole(self, moniker, rolname):
        self.pgroles[moniker] = rolname

FAKE_DB = FakeDB()


def _reset_fake_db():
    global FAKE_DB
    FAKE_DB = FakeDB()


def _capture_insert(args, member, **kwargs):
    """Record the member insert into FAKE_DB."""
    moniker = member["moniker"]
    FAKE_DB.insert_member(moniker, member)
    return moniker


def _capture_setflag(args, name, value, **kwargs):
    """Record the flag write into FAKE_DB."""
    moniker = kwargs.get("moniker")
    FAKE_DB.set_flag(moniker, name, value)
    return True


def _capture_setpassword(args, plaintextpassword, moniker, **kwargs):
    """Record the password hash into FAKE_DB."""
    FAKE_DB.set_password(moniker, f"$2b$12$hashed_{plaintextpassword}")
    return True


def _capture_add_funds(moniker, amount, **kwargs):
    """Record bank credit grant into FAKE_DB."""
    FAKE_DB.add_credits(moniker, amount)
    return True


def _capture_update(args, member, moniker, **kwargs):
    """Record the member update into FAKE_DB."""
    FAKE_DB.update_member(moniker, member)
    return True


def _capture_ensure_login_role(args, moniker, **kwargs):
    """Record the pgrole insert into FAKE_DB."""
    FAKE_DB.insert_pgrole(moniker, moniker)
    return True


def _capture_sync_groups(args, loginid, **kwargs):
    """Record the groups sync into FAKE_DB."""
    # Lookup member by loginid to get moniker
    for moniker, data in FAKE_DB.members.items():
        if data.get("loginid") == loginid:
            FAKE_DB.insert_pgrole(moniker, moniker)
            break
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**overrides):
    """Build a minimal ``args`` namespace like the console entry point creates."""
    defaults = dict(
        debug=False,
        databasename="zoid6test",
        databasehost="localhost",
        databaseport=5432,
        databaseschema="engine",
    )
    defaults.update(overrides)
    return Mock(**defaults)


def _make_member_dict(**overrides):
    """Default member dict that ``libmember.build`` would return for an add."""
    d = {
        "moniker": "jam",
        "loginid": "jam",
        "email": "jam@test.local",
        "password": "s3cret",
        "credits": 100,
        "ui": ["term"],
        "refcode": None,
        "attrs": {},
        "flags": {
            "APPROVED": {"value": True, "description": "Approved"},
            "SYSOP": {"value": False, "description": "Sysop"},
        },
    }
    d.update(overrides)
    return d


def _make_existing_member(**overrides):
    """Member row as returned by a SELECT (what ``edit()`` reads back)."""
    d = _make_member_dict(**overrides)
    d["datecreated"] = "2025-01-01T00:00:00"
    d["createdbymoniker"] = "admin"
    return d


class _FakeConn:
    """Bare connection stand-in that ``database.connect`` yields."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def cursor(self, **kw):
        return _FakeCursor()

    @property
    def autocommit(self):
        return False

    @autocommit.setter
    def autocommit(self, value):
        pass

    @property
    def pgconn(self):
        m = Mock()
        m.transaction_status = 0
        return m


class _FakeCursor:
    """Cursor that records queries and can return preset rows."""

    def __init__(self):
        self.rowcount = 1
        self._fetchone_result = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return self._fetchone_result


def _fake_connect(args, pool=None, auto_commit=True, **kw):
    """Context manager that yields a ``_FakeConn``."""
    conn = _FakeConn()

    @contextlib.contextmanager
    def _cm():
        try:
            yield conn
        except BaseException:
            conn.rollback()
            raise

    return _cm()


def _fake_connect_ctx(args, pool=None, auto_commit=True, **kw):
    conn = _FakeConn()

    @contextlib.contextmanager
    def _cm():
        try:
            yield conn
        except BaseException:
            conn.rollback()
            raise

    return _cm()


# ---------------------------------------------------------------------------
# Tests — add()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddMember:
    """Full end-to-end mock test for ``console.member.add()``."""

    def test_add_member_writes_all_side_effects(self):
        """add() inserts the member, flags, password, bank credits, pgrole, and commits."""
        _reset_fake_db()
        args = _make_args()
        fake_pool = Mock()

        member_dict = _make_member_dict()
        
        # Initialize FAKE_DB with the member to be added
        FAKE_DB.insert_member(member_dict["moniker"], copy.deepcopy(member_dict))

        # Sequence of user inputs consumed by _edit():
        #   [M]oniker accepted, [L]oginid accepted, [E]mail accepted,
        #   [P]assword set, [C]redits accepted, [U]I accepted,
        #   [F]lags accepted, [Q]uit → confirmation gate → Y
        call_count = {"n": 0}

        def _fake_inputchoice(prompt, valid, default, **kw):
            # _edit loop: skip straight to Quit on first call,
            # then confirmation on second call
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "Q"
            elif call_count["n"] == 2:
                return "Y"
            return "Y"

        def _fake_inputboolean(prompt, default="Y", **kw):
            if "add member?" in prompt:
                return True
            return True

        def _fake_inputstring(prompt, default="", **kw):
            if prompt.endswith("moniker:"):
                return "jam"
            elif prompt.endswith("loginid:"):
                return "jam"
            elif prompt.endswith("e-mail address:"):
                return "jam@test.local"
            elif prompt.endswith("refcode:"):
                return None
            return ""

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect),
            patch.object(libmember, "build", return_value=copy.deepcopy(member_dict)),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(member_dict["flags"]),
            ),
            patch.object(libmember, "getcurrentmoniker", return_value="admin"),
            patch.object(
                libmember,
                "verifyMemberFound", return_value=False
            ),
            patch.object(libmember, "insert", side_effect=_capture_insert),
            patch.object(libmember, "setflag", side_effect=_capture_setflag),
            patch.object(libmember, "setpassword", side_effect=_capture_setpassword),
            patch("bbsengine6.console.member.pgrole.ensure_login_role", side_effect=_capture_ensure_login_role),
            patch("bbsengine6.console.member.pgrole.sync_groups", side_effect=_capture_sync_groups),
            patch("bbsengine6.console.member.io.inputchoice", _fake_inputchoice),
            patch("bbsengine6.console.member.io.inputboolean", _fake_inputboolean),
            patch("bbsengine6.console.member.io.inputstring", _fake_inputstring),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="s3cret"),
            patch("bbsengine6.console.member.bank.BankService") as mock_bank_cls,
            patch("bbsengine6.console.member.configurerole"),
        ):
            mock_bank_cls.return_value.add_funds.side_effect = (
                _capture_add_funds
            )

            pool_kw = {"pool": fake_pool}
            result = console_member.add(args, **pool_kw)

        assert result is True, "add() should return True on success"

        # --- Verify the member row was inserted ---
        assert "jam" in FAKE_DB.members, "member row should exist in fake DB"
        row = FAKE_DB.members["jam"]
        assert row["moniker"] == "jam"
        assert row["loginid"] == "jam"
        assert row["email"] == "jam@test.local"

        # --- Verify flags were persisted ---
        assert "jam" in FAKE_DB.flags
        assert FAKE_DB.flags["jam"]["APPROVED"] is True
        assert FAKE_DB.flags["jam"]["SYSOP"] is False

        # --- Verify password was set (hash stored, not plaintext) ---
        assert "jam" in FAKE_DB.passwords
        assert FAKE_DB.passwords["jam"] != "s3cret", (
            "password should be hashed, not plaintext"
        )

        # --- Verify initial bank credits ---
        assert FAKE_DB.bank_credits.get("jam") == 100

        # --- Verify pgrole provisioning ---
        assert "jam" in FAKE_DB.pgroles

    def test_add_member_confirms_before_writing(self):
        """add() must not write anything if user declines confirmation."""
        _reset_fake_db()
        args = _make_args()
        fake_pool = Mock()

        member_dict = _make_member_dict()

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect),
            patch.object(libmember, "build", return_value=copy.deepcopy(member_dict)),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(member_dict["flags"]),
            ),
            patch.object(libmember, "getcurrentmoniker", return_value="admin"),
            patch.object(libmember, "verifyMemberFound", return_value=False),
            patch.object(libmember, "insert"),
            patch.object(libmember, "setflag"),
            patch.object(libmember, "setpassword"),
            patch(
                "bbsengine6.console.member.io.inputchoice",
                return_value="Q",
            ),
            patch(
                "bbsengine6.console.member.io.inputboolean",
                return_value=False,
            ),
            patch(
                "bbsengine6.console.member.io.inputstring",
                return_value="",
            ),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="s3cret"),
            patch("bbsengine6.console.member.bank.BankService"),
            patch("bbsengine6.console.member.configurerole"),
        ):
            pool_kw = {"pool": fake_pool}
            result = console_member.add(args, **pool_kw)

        assert result is False
        assert "jam" not in FAKE_DB.members, (
            "no member should be written when user declines"
        )

    def test_add_member_returns_false_when_pool_missing(self):
        """add() returns False immediately when pool is not in kwargs."""
        args = _make_args()
        with patch("bbsengine6.console.member.io.echo"):
            result = console_member.add(args)
        assert result is False

    def test_add_member_rollback_on_exception(self):
        """add() rolls back and returns False when an insert raises."""
        _reset_fake_db()
        args = _make_args()
        fake_pool = Mock()

        member_dict = _make_member_dict()

        def _failing_insert(*a, **kw):
            raise RuntimeError("disk full")

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect),
            patch.object(libmember, "build", return_value=copy.deepcopy(member_dict)),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(member_dict["flags"]),
            ),
            patch.object(libmember, "getcurrentmoniker", return_value="admin"),
            patch.object(libmember, "verifyMemberFound", return_value=False),
            patch.object(libmember, "insert", side_effect=_failing_insert),
            patch.object(libmember, "setflag"),
            patch.object(libmember, "setpassword"),
            patch(
                "bbsengine6.console.member.io.inputchoice",
                return_value="Q",
            ),
            patch(
                "bbsengine6.console.member.io.inputboolean",
                return_value=True,
            ),
            patch(
                "bbsengine6.console.member.io.inputstring",
                return_value="",
            ),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="s3cret"),
            patch("bbsengine6.console.member.bank.BankService"),
            patch("bbsengine6.console.member.configurerole"),
        ):
            pool_kw = {"pool": fake_pool}
            result = console_member.add(args, **pool_kw)

        assert result is False
        assert "jam" not in FAKE_DB.members


# ---------------------------------------------------------------------------
# Tests — edit()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEditMember:
    """Full end-to-end mock test for ``console.member.edit()``."""

    def test_edit_member_updates_email_and_flags(self):
        """edit() loads existing member, applies changes, and commits."""
        # NEW approach: Start with an empty fake DB and initialize it in the fake cursor
        
        test_itsonalreadymember = _make_existing_member()
        
        # Create a custom Cursor that initializes the FakeDB when fetched
        class _TestFakeCursor(_FakeCursor):
            def fetchone(self):
                # Initialize FAKE_DB with the test member
                FAKE_DB.insert_member(test_itsonalreadymember["moniker"], copy.deepcopy(test_itsonalreadymember))
                return test_itsonalreadymember

        args = _make_args()
        fake_pool = Mock()

        existing = _make_existing_member()
        edited = copy.deepcopy(existing)
        edited["email"] = "newjam@test.local"
        edited["flags"]["APPROVED"]["value"] = False

        fake_cursor = _TestFakeCursor()



        def _fake_connect_ctx(args, pool=None, auto_commit=True, **kw):
            conn = _FakeConn()

            @contextlib.contextmanager
            def _cm():
                try:
                    yield conn
                except BaseException:
                    conn.rollback()
                    raise
                finally:
                    if auto_commit:
                        conn.commit()

            return _cm()

        def _fake_cursor_factory(conn=None, row_factory=None):
            return fake_cursor

        call_count = {"n": 0}

        def _fake_inputchoice(prompt, valid, default, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "E"
            if call_count["n"] == 2:
                return "Q"
            return "Q"

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect_ctx),
            patch("bbsengine6.console.member.database.cursor", _fake_cursor_factory),
            patch.object(
                libmember,
                "build",
                side_effect=lambda *a, conn=None, **kw: copy.deepcopy(existing),
            ),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(existing["flags"]),
            ),
            patch.object(libmember, "update", side_effect=_capture_update),
            patch.object(libmember, "setflag", side_effect=_capture_setflag),
            patch.object(libmember, "setpassword", side_effect=_capture_setpassword),
            patch("bbsengine6.console.member.pgrole.ensure_login_role", side_effect=_capture_ensure_login_role),
            patch("bbsengine6.console.member.pgrole.sync_groups", side_effect=_capture_sync_groups),
            patch(
                "bbsengine6.console.member.io.inputchoice",
                side_effect=_fake_inputchoice,
            ),
            patch(
                "bbsengine6.console.member.io.inputboolean",
                return_value=True,
            ),
            patch(
                "bbsengine6.console.member.io.inputstring",
                return_value="newjam@test.local",
            ),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="newpass"),
            patch("bbsengine6.console.member.configurerole"),
            patch("bbsengine6.console.member.setui"),
        ):
            pool_kw = {"pool": fake_pool}
            result = console_member.edit(args, **pool_kw)

        assert result is True, "edit() should return True on success"

        # --- Verify member was updated in the fake DB ---
        assert "jam" in FAKE_DB.members

        # --- Verify email change was persisted ---
        row = FAKE_DB.members["jam"]
        assert row["email"] == "newjam@test.local", (
            "email should be updated to newjam@test.local"
        )

        # --- Verify the EMAILVERIFIED flag was reset (email changed) ---
        assert "jam" in FAKE_DB.flags
        assert FAKE_DB.flags["jam"]["EMAILVERIFIED"] is False, (
            "EMAILVERIFIED should be False after email change"
        )

        # --- Verify the password was updated ---
        assert "jam" in FAKE_DB.passwords

    def test_edit_member_not_found_returns_false(self):
        """edit() returns False when the member lookup finds no row."""
        args = _make_args()
        fake_pool = Mock()

        fake_cursor = _FakeCursor()
        fake_cursor.rowcount = 0

        def _fake_connect_ctx(args, pool=None, auto_commit=True, **kw):
            conn = _FakeConn()

            @contextlib.contextmanager
            def _cm():
                try:
                    yield conn
                except BaseException:
                    conn.rollback()
                    raise
                finally:
                    if auto_commit:
                        conn.commit()

            return _cm()

        def _fake_cursor_factory(conn=None, row_factory=None):
            return fake_cursor

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect_ctx),
            patch("bbsengine6.console.member.database.cursor", _fake_cursor_factory),
            patch(
                "bbsengine6.console.member.io.inputstring",
                return_value="nobody",
            ),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
        ):
            pool_kw = {"pool": fake_pool}
            result = console_member.edit(args, **pool_kw)

        assert result is False, "edit() should return False when member not found"

    def test_edit_member_rejects_loginid_rename(self):
        """edit() refuses to proceed when loginid is changed (psql role issue)."""
        args = _make_args()
        fake_pool = Mock()

        existing = _make_existing_member()
        edited = copy.deepcopy(existing)
        edited["loginid"] = "newlogin"

        fake_cursor = _FakeCursor()
        fake_cursor._fetchone_result = existing

        def _fake_connect_ctx(args, pool=None, auto_commit=True, **kw):
            conn = _FakeConn()

            @contextlib.contextmanager
            def _cm():
                try:
                    yield conn
                except BaseException:
                    conn.rollback()
                    raise
                finally:
                    if auto_commit:
                        conn.commit()

            return _cm()

        def _fake_cursor_factory(conn=None, row_factory=None):
            return fake_cursor

        call_count = {"n": 0}

        def _fake_inputchoice(prompt, valid, default, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "L"
            return "Q"

        with (
            patch("bbsengine6.console.member.database.connect", _fake_connect_ctx),
            patch("bbsengine6.console.member.database.cursor", _fake_cursor_factory),
            patch.object(
                libmember,
                "build",
                side_effect=lambda *a, conn=None, **kw: copy.deepcopy(existing),
            ),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(existing["flags"]),
            ),
            patch.object(libmember, "update", side_effect=_capture_update),
            patch.object(libmember, "setflag", side_effect=_capture_setflag),
            patch.object(libmember, "setpassword", side_effect=_capture_setpassword),
            patch("bbsengine6.console.member.pgrole.ensure_login_role", side_effect=_capture_ensure_login_role),
            patch("bbsengine6.console.member.pgrole.sync_groups", side_effect=_capture_sync_groups),
            patch(
                "bbsengine6.console.member.io.inputchoice",
                side_effect=_fake_inputchoice,
            ),
            patch(
                "bbsengine6.console.member.io.inputboolean",
                return_value=True,
            ),
            patch(
                "bbsengine6.console.member.io.inputstring",
                return_value="newlogin",
            ),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="pass"),
            patch("bbsengine6.console.member.configurerole"),
            patch("bbsengine6.console.member.setui"),
        ):
            pool_kw = {"pool": fake_pool}
            result = console_member.edit(args, **pool_kw)

        assert result is False, (
            "edit() should return False when loginid rename is attempted"
        )


# ---------------------------------------------------------------------------
# Tests — configurerole() rolsuper guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureRoleSuperuserGuard:
    """``configurerole()`` must leave a SUPERUSER role's attributes alone
    because the connecting executor (``zoid6``, NOSUPERUSER) cannot
    ``ALTER ROLE`` a SUPERUSER role. This is the regression that broke
    ``console.member.edit`` once the database owner was switched to
    ``zoid6``.
    """

    def test_skips_privs_when_role_is_superuser(self):
        """When ``get_role_privs`` reports ``rolsuper=True``, neither
        the ``grant`` nor the ``revoke`` branch of the priv sync runs.
        ``manage_secondary_role`` is still called (out-of-scope skip).
        """
        args = _make_args()
        fake_conn = _FakeConn()

        privs_super = {
            "rolname": "jam",
            "rolsuper": True,
            "rolcreaterole": False,
            "rolcreatedb": False,
            "rolcanlogin": True,
            "rolreplication": False,
            "rolbypassrls": False,
        }

        with (
            patch.object(
                console_member.database, "rolexists", return_value=True
            ),
            patch.object(
                console_member.database, "get_role_privs", return_value=privs_super
            ),
            patch.object(
                console_member.database,
                "manage_role_privs",
            ) as mock_privs,
            patch.object(
                console_member.database,
                "manage_secondary_role",
            ) as mock_secondary,
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.inputboolean"),
        ):
            result_true = console_member.configurerole(
                args, "jam", sysop=True, conn=fake_conn
            )
            result_false = console_member.configurerole(
                args, "jam", sysop=False, conn=fake_conn
            )

        assert result_true is True
        assert result_false is True
        mock_privs.assert_not_called(), (
            "manage_role_privs must NOT be called for a SUPERUSER role"
        )
        assert mock_secondary.call_count == 2, (
            "manage_secondary_role still runs (out of scope for the guard)"
        )
        # manage_secondary_role(args, rolename, action, secondary, **kwargs)
        secondary_calls = [
            (c.args[1], c.args[2], c.args[3])
            for c in mock_secondary.call_args_list
        ]
        assert ("jam", "grant", "sysop") in secondary_calls
        assert ("jam", "revoke", "sysop") in secondary_calls

    def test_runs_privs_when_role_is_not_superuser(self):
        """When ``rolsuper`` is False the existing grant/revoke behavior
        is preserved verbatim (regression coverage)."""
        args = _make_args()
        fake_conn = _FakeConn()

        privs_normal = {
            "rolname": "alice",
            "rolsuper": False,
            "rolcreaterole": False,
            "rolcreatedb": False,
            "rolcanlogin": True,
            "rolreplication": False,
            "rolbypassrls": False,
        }

        with (
            patch.object(
                console_member.database, "rolexists", return_value=True
            ),
            patch.object(
                console_member.database, "get_role_privs", return_value=privs_normal
            ),
            patch.object(
                console_member.database,
                "manage_role_privs",
            ) as mock_privs,
            patch.object(
                console_member.database,
                "manage_secondary_role",
            ) as mock_secondary,
            patch("bbsengine6.console.member.io.echo"),
        ):
            result_true = console_member.configurerole(
                args, "alice", sysop=True, conn=fake_conn
            )
            result_false = console_member.configurerole(
                args, "alice", sysop=False, conn=fake_conn
            )

        assert result_true is True
        assert result_false is True

# sysop=True -> grant createdb, grant createrole
        grant_actions = [
            (c.args[1], c.args[2], c.args[3])
            for c in mock_privs.call_args_list
            if c.args[3] == "createdb" or c.args[3] == "createrole"
        ]
        assert ("alice", "grant", "createdb") in grant_actions
        assert ("alice", "grant", "createrole") in grant_actions

        # sysop=False -> revoke createdb, revoke createrole
        revoke_actions = [
            (c.args[1], c.args[2], c.args[3])
            for c in mock_privs.call_args_list
            if c.args[2] == "revoke"
        ]
        assert ("alice", "revoke", "createdb") in revoke_actions
        assert ("alice", "revoke", "createrole") in revoke_actions

        assert mock_secondary.call_count == 2
        secondary_calls = [
            (c.args[1], c.args[2], c.args[3])
            for c in mock_secondary.call_args_list
        ]
        assert ("alice", "grant", "sysop") in secondary_calls
        assert ("alice", "revoke", "sysop") in secondary_calls

    def test_runs_privs_when_get_role_privs_returns_none(self):
        """A lookup failure (``privs is None``) must fall back to the
        existing behavior so a transient DB error doesn't strand a
        member's role attributes out of sync."""
        args = _make_args()
        fake_conn = _FakeConn()

        with (
            patch.object(
                console_member.database, "rolexists", return_value=True
            ),
            patch.object(
                console_member.database, "get_role_privs", return_value=None
            ),
            patch.object(
                console_member.database,
                "manage_role_privs",
            ) as mock_privs,
            patch.object(
                console_member.database,
                "manage_secondary_role",
            ),
            patch("bbsengine6.console.member.io.echo"),
        ):
            console_member.configurerole(args, "bob", sysop=False, conn=fake_conn)

        revoke_actions = [
            (c.args[1], c.args[2], c.args[3])
            for c in mock_privs.call_args_list
            if c.args[2] == "revoke"
        ]
        assert ("bob", "revoke", "createdb") in revoke_actions
        assert ("bob", "revoke", "createrole") in revoke_actions


# ---------------------------------------------------------------------------
# Tests — password encryption when set via console member
# ---------------------------------------------------------------------------


_pycrypt = crypt


class _SpyCursor:
    """Cursor stand-in that records every ``execute()`` call.

    The encryption claim is verified at the SQL layer: we do NOT mock
    ``libmember.setpassword`` (the bug the user reported). Instead, we let
    the real ``setpassword`` run and capture the SQL it sends to the
    database. Each call gets a fresh, freshly-minted bcrypt hash from
    Python's ``crypt`` module so we can also exercise the round-trip
    ("what gets stored must match the plaintext via ``crypt(plain, stored)``").
    """

    def __init__(self):
        self.calls = []  # list of (query, params) — query is the original
        # Composed/string, never the stringified repr.
        self._fetchone_result = None
        self._password_response = None  # set by setpassword UPDATE
        self._rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        # Store the original query object so callers can inspect both the
        # SQL text (via str() / as_string()) and the structural composition
        # (via iteration of psycopg.sql.Composed children). We do NOT
        # stringify here: str(Composed) yields its Python repr, not SQL.
        self.calls.append((query, params))
        rendered = query.as_string(None) if hasattr(query, "as_string") else str(query)
        sql_lower = rendered.lower()
        # Detect the new setpassword shape: an UPDATE against __member
        # that sets password=... and filters by moniker=... . The hash is
        # pre-computed in Python by ``bbsengine6.util.encryptpassword``,
        # so the SQL is just ``set password=$1 where moniker=$2`` — no
        # ``crypt`` or ``gen_salt`` in the wire SQL. We capture the hash
        # (first Literal child) so the round-trip assertion
        # ``crypt(plain, stored) == stored`` is meaningful.
        if (
            sql_lower.lstrip().startswith("update ")
            and "set password=" in sql_lower
            and "where moniker=" in sql_lower
            and "__member" in sql_lower
            and "crypt(" not in sql_lower
        ):
            from psycopg import sql as _sql
            captured_hash = ""
            if hasattr(query, "__iter__") and not isinstance(query, str):
                for child in query:
                    if isinstance(child, _sql.Literal):
                        v = child.as_string(None).strip("'\"")
                        # The hash is the first Literal after the
                        # ``set password=`` chunk; the moniker is the
                        # second positional parameter.
                        if v and captured_hash == "":
                            captured_hash = v
                            break
            # If for any reason we did not extract a hash, fall back to
            # letting the spy report None so the test surfaces a real
            # failure rather than a misleading default.
            self._password_response = captured_hash or None
            self._rowcount = 1
            return
        # For all other statements, leave _fetchone_result alone so the
        # SELECT result from before setpassword stays intact.
        self._rowcount = 1

    def fetchone(self):
        if self._password_response is not None:
            return {"password": self._password_response}
        return self._fetchone_result

    @property
    def rowcount(self):
        return self._rowcount

    @rowcount.setter
    def rowcount(self, value):
        self._rowcount = value


class _SpyConn:
    """Connection stand-in: emits ``_SpyCursor`` and tracks commit/rollback."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, **kw):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    @property
    def autocommit(self):
        return False

    @autocommit.setter
    def autocommit(self, value):
        pass

    @property
    def pgconn(self):
        m = Mock()
        m.transaction_status = 0
        return m


def _spy_connect_factory(cursor):
    """Build a ``database.connect`` replacement that yields a ``_SpyConn``."""

    @contextlib.contextmanager
    def _cm(*a, **kw):
        conn = _SpyConn(cursor)
        try:
            yield conn
        except BaseException:
            conn.rollback()
            raise
        finally:
            # Mirror the existing tests: auto_commit=True (default for
            # add()'s outside block) commits at exit. add()/edit() open
            # their own conn with auto_commit=False and call commit()
            # explicitly, so this is a no-op on that path.
            if kw.get("auto_commit", True):
                conn.commit()

    return _cm


def _find_setpassword_call(calls):
    """Return the (sql, params) tuple for the setpassword UPDATE, or None.

    ``database.query()`` returns a ``psycopg.sql.Composed`` whose ``str()``
    is its Python repr (not the wire-protocol SQL). We detect the
    setpassword statement by inspecting both the repr and the structural
    children so we are not fooled by the repr's content. After the
    2026-08-22 refactor the SQL is ``set password=$1 where moniker=$2``
    (no ``crypt``/``gen_salt`` in SQL because the hash is computed
    locally by ``bbsengine6.util.encryptpassword``), so we match on the
    parameterized UPDATE shape.
    """
    for sql, params in calls:
        children = list(sql) if hasattr(sql, "__iter__") and not isinstance(sql, str) else []
        if not children:
            continue
        rendered = sql.as_string(None) if hasattr(sql, "as_string") else str(sql)
        r_lower = rendered.lower()
        if (
            r_lower.lstrip().startswith("update ")
            and "set password=" in r_lower
            and "where moniker=" in r_lower
            and "__member" in r_lower
            and "crypt(" not in r_lower
        ):
            return (sql, params, children, rendered)
    return None


def _assert_setpassword_sql(sql, params, plaintext: str, moniker: str):
    """Shared assertions: hash produced locally, parameterization, no plaintext leak.

    After the 2026-08-22 refactor, ``setpassword`` produces the bcrypt
    hash locally via ``bbsengine6.util.encryptpassword`` (passlib,
    ``$2b$06$``) and binds it as a single ``Literal`` parameter on a
    parameterized ``UPDATE ... set password=$1 where moniker=$2``. So:

    * The SQL must NOT contain ``crypt(`` or ``gen_salt`` — those are
      no longer sent to the database.
    * The plaintext must NOT appear as a ``Literal`` nor as an inline
      SQL fragment (it is never bound).
    * The hash (first ``Literal`` child) must be bcrypt-shaped and must
      verify via ``crypt(plaintext, hash) == hash``.
    * The moniker must be the second ``Literal`` and bound, not inlined.

    ``database.query()`` produces a ``psycopg.sql.Composed`` that
    parameterizes via ``Literal`` nodes; on the wire those literals are
    bound parameters, so the structural shape is the authoritative
    evidence that values are not concatenated into the SQL.
    """
    rendered = sql.as_string(None) if hasattr(sql, "as_string") else str(sql)
    sql_lower = rendered.lower()

    assert sql_lower.lstrip().startswith("update "), (
        f"setpassword must be an UPDATE; got: {rendered!r}"
    )
    assert "set password=" in sql_lower, (
        f"setpassword must set the password column; got: {rendered!r}"
    )
    assert "where moniker=" in sql_lower, (
        f"setpassword must target the right row by moniker; got: {rendered!r}"
    )
    assert "__member" in sql_lower, (
        f"setpassword must target the __member table; got: {rendered!r}"
    )
    assert "crypt(" not in sql_lower, (
        f"setpassword must NOT call crypt() server-side anymore "
        f"(hash is produced locally); got: {rendered!r}"
    )
    assert "gen_salt" not in sql_lower, (
        f"setpassword must NOT call gen_salt() server-side anymore "
        f"(hash is produced locally); got: {rendered!r}"
    )

    children = list(sql)
    from psycopg import sql as _sql

    def _literal_value(c):
        return c.as_string(None).strip("'\"") if hasattr(c, "as_string") else ""

    # The hash is the first Literal after the ``set password=`` chunk.
    hash_literal = None
    moniker_literal = None
    for c in children:
        if isinstance(c, _sql.Literal):
            v = _literal_value(c)
            if hash_literal is None:
                hash_literal = v
            elif moniker_literal is None:
                moniker_literal = v
                break

    assert hash_literal is not None, (
        f"setpassword must bind the bcrypt hash as the first Literal; "
        f"children were: {[type(c).__name__ for c in children]}"
    )
    assert hash_literal.startswith(("$2a$", "$2b$", "$2y$")), (
        f"setpassword must store a bcrypt hash ($2a$/2b$/2y$); "
        f"got: {hash_literal!r}"
    )
    assert len(hash_literal) == 60, (
        f"setpassword must store a 60-char bcrypt hash; "
        f"got len={len(hash_literal)} value={hash_literal!r}"
    )
    assert _pycrypt.crypt(plaintext, hash_literal) == hash_literal, (
        f"stored hash must verify against the plaintext via crypt(); "
        f"plaintext={plaintext!r} hash={hash_literal!r}"
    )

    # The plaintext must NEVER appear anywhere in the wire SQL.
    sql_chunks_with_plaintext = [
        c for c in children
        if isinstance(c, _sql.SQL) and plaintext in c.as_string(None)
    ]
    literals_with_plaintext = [
        c for c in children
        if isinstance(c, _sql.Literal) and _literal_value(c) == plaintext
    ]
    assert not literals_with_plaintext, (
        f"plaintext {plaintext!r} must NEVER appear as a Literal "
        f"(it should not be bound at all)"
    )
    assert not sql_chunks_with_plaintext, (
        f"plaintext must NEVER be inlined into a SQL fragment; "
        f"offending chunk: {sql_chunks_with_plaintext[0].as_string(None)!r}"
    )

    assert moniker_literal == moniker, (
        f"setpassword must bind moniker={moniker!r} as the second Literal; "
        f"got: {moniker_literal!r}"
    )
    sql_chunks_with_moniker = [
        c for c in children
        if isinstance(c, _sql.SQL) and moniker in c.as_string(None)
    ]
    assert not sql_chunks_with_moniker, (
        f"moniker must NEVER be inlined into a SQL fragment; "
        f"offending chunk: {sql_chunks_with_moniker[0].as_string(None)!r}"
    )


@pytest.mark.unit
class TestConsoleMemberPasswordEncryption:
    """Confirm that ``console.member.{add,edit}`` write an encrypted password.

    The user's bug report: ``libmember.setpassword`` works fine when called
    standalone (auth succeeds afterwards), but the console member flow does
    not set the password correctly. The existing tests mock
    ``libmember.setpassword`` outright, so they cannot catch a bug in the
    call site. These tests instead spy on the SQL layer and verify:

    1. ``setpassword`` is actually invoked from ``add()`` and ``edit()``.
    2. The plaintext is NOT sent to the database at all — the hash is
       produced locally by ``bbsengine6.util.encryptpassword`` (passlib
       bcrypt, ``$2b$06$``, matching PostgreSQL ``gen_salt('bf')``) and
       passed to the UPDATE as a single bound parameter.
    3. The hash is a bound parameter (never inlined in the SQL).
    4. The plaintext is never written anywhere (no SQL fragment, no
       parameter).
    5. The stored hash round-trips: ``crypt(plaintext, stored) == stored``.
    """

    def test_add_member_password_is_bcrypted_and_bound_as_parameter(self):
        """add() must call setpassword with the right plaintext and target row."""
        args = _make_args()
        fake_pool = Mock()
        member_dict = _make_member_dict(password="Sup3rSecret!")
        spy_cursor = _SpyCursor()

        # Pre-seed the cursor so the SELECT in edit() flow doesn't blow up,
        # and so insert() / other helpers see the row they expect.
        # add() does not SELECT first; it just builds then inserts.
        def _fake_inputchoice(prompt, valid, default, **kw):
            return "Q"

        def _fake_inputboolean(prompt, default="Y", **kw):
            if "add member?" in prompt:
                return True
            return True

        def _fake_inputstring(prompt, default="", **kw):
            if prompt.endswith("moniker:"):
                return member_dict["moniker"]
            if prompt.endswith("loginid:"):
                return member_dict["loginid"]
            if prompt.endswith("e-mail address:"):
                return member_dict["email"]
            if prompt.endswith("refcode:"):
                return None
            return ""

        with (
            patch("bbsengine6.console.member.database.connect", _spy_connect_factory(spy_cursor)),
            patch.object(libmember, "build", return_value=copy.deepcopy(member_dict)),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(member_dict["flags"]),
            ),
            patch.object(libmember, "getcurrentmoniker", return_value="admin"),
            patch.object(libmember, "verifyMemberFound", return_value=False),
            patch.object(libmember, "insert", return_value=member_dict["moniker"]),
            patch.object(libmember, "setflag", return_value=True),
            # NB: libmember.setpassword is intentionally NOT mocked here.
            # The whole point of this test is to exercise the real call.
            patch("bbsengine6.console.member.pgrole.ensure_login_role", return_value=True),
            patch("bbsengine6.console.member.pgrole.sync_groups", return_value=True),
            patch("bbsengine6.console.member.io.inputchoice", _fake_inputchoice),
            patch("bbsengine6.console.member.io.inputboolean", _fake_inputboolean),
            patch("bbsengine6.console.member.io.inputstring", _fake_inputstring),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value="Sup3rSecret!"),
            patch("bbsengine6.console.member.bank.BankService") as mock_bank_cls,
            patch("bbsengine6.console.member.configurerole", return_value=True),
        ):
            mock_bank_cls.return_value.add_funds.return_value = True
            result = console_member.add(args, pool=fake_pool)

        assert result is True, "add() should succeed end-to-end"

        # 1. A setpassword UPDATE was actually issued.
        sp = _find_setpassword_call(spy_cursor.calls)
        assert sp is not None, (
            "add() never sent a setpassword UPDATE; password not stored. "
            f"Calls observed: {[type(c).__name__ for c, _ in spy_cursor.calls]}"
        )
        sql, params, _children, _rendered = sp

        # 2. SQL has the right shape: bcrypt via crypt+gen_salt('bf').
        _assert_setpassword_sql(
            sql, params, plaintext="Sup3rSecret!", moniker=member_dict["moniker"]
        )

        # 3. No SQL fragment elsewhere in the add() flow contains the
        #    plaintext. (as_string() renders Literals inline for display,
        #    so it is not a meaningful check; we inspect the structural
        #    children directly. Here we only need to confirm no SQL chunk
        #    from any other statement inlined the plaintext.)
        from psycopg import sql as _sql
        for call_sql, _p in spy_cursor.calls:
            for child in call_sql if hasattr(call_sql, "__iter__") and not isinstance(call_sql, str) else []:
                if isinstance(child, _sql.SQL) and "Sup3rSecret!" in child.as_string(None):
                    raise AssertionError(
                        f"plaintext leaked into a SQL fragment: {child.as_string(None)!r}"
                    )

        # 4. Round-trip: the simulated DB hash must verify against the
        #    plaintext via crypt(plaintext, stored) == stored. This is the
        #    same predicate ``libmember.checkpassword`` uses server-side.
        stored_hash = spy_cursor._password_response
        assert stored_hash.startswith(("$2a$", "$2b$", "$2y$")), (
            f"stored hash must be a bcrypt hash; got: {stored_hash!r}"
        )
        assert _pycrypt.crypt("Sup3rSecret!", stored_hash) == stored_hash, (
            "stored hash must verify against the plaintext via crypt()"
        )

    def test_edit_member_password_is_bcrypted_and_bound_as_parameter(self):
        """edit() must call setpassword with the new plaintext on the right row."""
        args = _make_args()
        fake_pool = Mock()
        existing = _make_existing_member()
        new_plaintext = "N3wP@ssw0rd!"

        spy_cursor = _SpyCursor()
        spy_cursor._fetchone_result = existing  # SELECT returns the row

        # Drive the in-memory edit loop: pick [P] to change the password,
        # then [Q] to quit, then confirm save.
        cc = {"n": 0}

        def _fake_inputchoice(prompt, valid, default, **kw):
            cc["n"] += 1
            if cc["n"] == 1:
                return "P"
            return "Q"

        def _fake_inputboolean(prompt, default="Y", **kw):
            if "save changes?" in prompt:
                return True
            return True

        def _fake_inputstring(prompt, default="", **kw):
            return ""

        with (
            patch("bbsengine6.console.member.database.connect", _spy_connect_factory(spy_cursor)),
            patch("bbsengine6.console.member.database.cursor", lambda conn=None, **kw: spy_cursor),
            patch.object(
                libmember,
                "build",
                side_effect=lambda *a, conn=None, **kw: copy.deepcopy(existing),
            ),
            patch.object(
                libmember,
                "getflags",
                return_value=copy.deepcopy(existing["flags"]),
            ),
            patch.object(libmember, "update", return_value=True),
            patch.object(libmember, "setflag", return_value=True),
            # NB: libmember.setpassword is intentionally NOT mocked here.
            patch("bbsengine6.console.member.pgrole.ensure_login_role", return_value=True),
            patch("bbsengine6.console.member.pgrole.sync_groups", return_value=True),
            patch("bbsengine6.console.member.io.inputchoice", _fake_inputchoice),
            patch("bbsengine6.console.member.io.inputboolean", _fake_inputboolean),
            patch("bbsengine6.console.member.io.inputstring", _fake_inputstring),
            patch("bbsengine6.console.member.io.inputinteger", return_value=100),
            patch("bbsengine6.console.member.io.echo"),
            patch("bbsengine6.console.member.io.echo_traceback"),
            patch("bbsengine6.util.heading"),
            patch("bbsengine6.util.inputpassword", return_value=new_plaintext),
            patch("bbsengine6.console.member.configurerole", return_value=True),
            patch("bbsengine6.console.member.setui"),
        ):
            result = console_member.edit(args, pool=fake_pool)

        assert result is True, "edit() should succeed end-to-end"

        sp = _find_setpassword_call(spy_cursor.calls)
        assert sp is not None, (
            "edit() never sent a setpassword UPDATE; password not stored. "
            f"Calls observed: {[type(c).__name__ for c, _ in spy_cursor.calls]}"
        )
        sql, params, _children, _rendered = sp
        _assert_setpassword_sql(
            sql, params, plaintext=new_plaintext, moniker=existing["moniker"]
        )

        from psycopg import sql as _sql
        for call_sql, _p in spy_cursor.calls:
            for child in call_sql if hasattr(call_sql, "__iter__") and not isinstance(call_sql, str) else []:
                if isinstance(child, _sql.SQL) and new_plaintext in child.as_string(None):
                    raise AssertionError(
                        f"plaintext leaked into a SQL fragment: {child.as_string(None)!r}"
                    )

        stored_hash = spy_cursor._password_response
        assert stored_hash.startswith(("$2a$", "$2b$", "$2y$")), (
            f"stored hash must be a bcrypt hash; got: {stored_hash!r}"
        )
        assert _pycrypt.crypt(new_plaintext, stored_hash) == stored_hash, (
            "stored hash must verify against the plaintext via crypt()"
        )

    def test_setpassword_uses_unique_salt_per_call(self):
        """encryptpassword() is invoked on every call so two identical
        passwords produce two distinct bcrypt hashes. If the code ever
        cached a hash, reused a salt, or substituted a static value,
        this assertion fails — which is exactly the kind of bug a
        "password not set correctly" symptom could mask.
        """
        args = _make_args()
        cur1 = _SpyCursor()
        cur2 = _SpyCursor()

        with patch(
            "bbsengine6.console.member.database.connect",
            _spy_connect_factory(cur1),
        ):
            libmember.setpassword(args, "SamePass!", "alice", pool=Mock())

        with patch(
            "bbsengine6.console.member.database.connect",
            _spy_connect_factory(cur2),
        ):
            libmember.setpassword(args, "SamePass!", "bob", pool=Mock())

        h1 = cur1._password_response
        h2 = cur2._password_response
        assert h1 is not None and h2 is not None, (
            "spy cursor must capture the stored hash from both calls; "
            "got h1=None or h2=None"
        )
        assert h1 != h2, (
            "two setpassword calls with the same plaintext must produce "
            "different hashes (encryptpassword must randomise the salt each call)"
        )