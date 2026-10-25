"""engine.log_action(): the single writer for engine.__actionlog.

No role inserts into the log directly. Each caller goes through this SECURITY DEFINER function,
owned by zoid6, which is the only role with insert on the table. The function validates the
action, and records the moniker and client address it is given. Its grants are the only ones
that let a role add a row.
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkfunctions

SQL = Path(pgrole.__file__).parent / "sql" / "log_action.sql"


@pytest.mark.unit
def test_writer_file_exists_and_is_named_for_the_function():
    assert SQL.is_file(), SQL


@pytest.mark.unit
def test_writer_is_security_definer_owned_by_zoid6():
    text = SQL.read_text()
    assert re.search(r"SECURITY DEFINER", text, re.I), "writer must run with its owner's rights"
    assert re.search(r"OWNER TO zoid6", text, re.I), "writer must be owned by zoid6"


@pytest.mark.unit
def test_writer_pins_search_path():
    # A SECURITY DEFINER function without a fixed search_path can be redirected by a caller.
    assert re.search(r"SET search_path\s*=", SQL.read_text(), re.I)


@pytest.mark.unit
def test_writer_signature_takes_moniker_action_address_and_note():
    text = SQL.read_text().lower()
    assert "engine.log_action(" in text
    for arg in ("p_moniker", "p_action", "p_remoteaddr", "p_note"):
        assert arg in text, arg


@pytest.mark.unit
def test_writer_inserts_into_the_action_log_table():
    text = SQL.read_text().lower()
    assert "insert into engine.__actionlog" in text


@pytest.mark.unit
def test_writer_rejects_an_unknown_action():
    text = SQL.read_text().lower()
    for action in ("login", "login_failed", "logout", "auth_expired"):
        assert f"'{action}'" in text, action
    assert "raise exception" in text


@pytest.mark.unit
def test_only_the_writer_is_granted_insert_and_no_role_gets_direct_insert():
    text = SQL.read_text().lower()
    assert "grant execute" in text
    assert not re.search(r"grant\s+[^;]*\binsert\b[^;]*on\s+engine\.__actionlog", text)


@pytest.mark.unit
def test_writer_is_in_the_checkfunctions_list():
    funcs = checkfunctions.__dict__
    src = Path(checkfunctions.__file__).read_text()
    assert '"engine.log_action"' in src, "writer must be installed by checkfunctions"
    assert funcs is not None
