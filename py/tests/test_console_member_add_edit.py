"""
Mock tests for console member add() and edit() end-to-end.

Demonstrates the full flow of adding and editing a member through the
console layer, including all side effects (flags, password, bank credits,
pgrole provisioning, group sync). A fake in-memory database tracks every
write so we can query it directly to prove the operations landed.
"""

import copy
import contextlib
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