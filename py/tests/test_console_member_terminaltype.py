"""Console member [Y] Terminal type: the view shows the value, and the edit accepts only
names that have a terminfo entry."""

from unittest.mock import patch

from bbsengine6.console import member as cm
from bbsengine6.io import terminfo


def _member(**extra):
    flags = {n: {"value": False, "description": n} for n in
             ["SYSOP", "MAGIC", "EROS", "AUTHENTICATED", "ASIMOV", "NOCALUMNI", "EMAILVERIFIED", "APPROVED"]}
    m = {"moniker": "alice", "loginid": "alice", "email": "a@x", "ui": ["term"], "credits": 0,
         "refcode": None, "flags": flags, "password": None, "psqlrole": None, "attrs": {},
         "terminaltype": "vt100"}
    m.update(extra)
    return m


def _render(m):
    out = []
    with patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=dict(m))
    return "\n".join(out)


def test_view_shows_stored_terminal_type():
    assert "Terminal type" in _render(_member())
    assert "vt100" in _render(_member())


def test_view_shows_default_when_unset():
    text = _render(_member(terminaltype=None))
    assert "xterm (default)" in text


def test_edit_accepts_valid_name(monkeypatch):
    monkeypatch.setattr(terminfo, "has_entry", lambda n: n == "vt220")
    monkeypatch.setattr(cm.io, "inputstring", lambda *a, **k: "vt220")
    assert cm._ask_terminaltype_menu("vt100") == "vt220"


def test_edit_rejects_unknown_name_and_keeps_stored(monkeypatch):
    monkeypatch.setattr(terminfo, "has_entry", lambda n: False)
    monkeypatch.setattr(cm.io, "inputstring", lambda *a, **k: "bogus")
    errors = []
    monkeypatch.setattr(cm.io, "echo", lambda *a, **k: errors.append(str(a[0]) if a else ""))
    assert cm._ask_terminaltype_menu("vt100") == "vt100"
    assert any("no terminfo entry" in e for e in errors)


def test_edit_blank_keeps_stored(monkeypatch):
    monkeypatch.setattr(cm.io, "inputstring", lambda *a, **k: "")
    assert cm._ask_terminaltype_menu("vt100") == "vt100"


def test_edit_key_is_in_the_menu_key_lists():
    import inspect

    src = inspect.getsource(cm._edit)
    assert '"LMECPFDTYURQX"' in src and "[MECPFDTYURQX]" in src
    assert 'ch == "Y"' in src
