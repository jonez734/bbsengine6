"""The edit menu's keys must agree: every key the loop accepts is shown, and every shown key is accepted.

The prompt, the accepted key set and the rendered menu lines were three separate literals, so
they could drift. A key accepted but not drawn (for example F) is invisible to the sysop.
"""

import copy
import importlib
import re
import sys
import unittest.mock as um
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
cm = importlib.import_module("bbsengine6.console.member")

ACCEPTED = "LMECPFDURQX"


def _member():
    flags = {n: {"value": False, "description": n} for n in
             ["SYSOP", "MAGIC", "EROS", "AUTHENTICATED", "ASIMOV", "NOCALUMNI", "EMAILVERIFIED", "APPROVED"]}
    return {"moniker": "jam", "loginid": "jam", "email": "j@x", "ui": ["term"], "credits": 100,
            "refcode": None, "flags": flags, "password": None, "psqlrole": None, "attrs": {}}


def _rendered_keys():
    out = []
    m = _member()
    with um.patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=copy.deepcopy(m))
    text = "\n".join(out)
    return set(re.findall(r"\[([A-Z])\]", text))


@pytest.mark.unit
def test_every_accepted_key_is_shown_in_the_menu():
    shown = _rendered_keys()
    missing = [k for k in ACCEPTED if k not in ("Q", "X") and k not in shown]
    assert missing == [], f"accepted but not shown: {missing}; shown: {sorted(shown)}"


@pytest.mark.unit
def test_prompt_lists_the_accepted_keys():
    src = Path(cm.__file__).read_text()
    m = re.search(r'\[(M[A-Z]+)\]\{\{var:promptcolor\}\}: \{\{var:inputcolor\}\}', src)
    assert m, "member edit prompt not found"
    assert set(m.group(1)) == set(ACCEPTED) - {"L"} | {"M"} or set(m.group(1)) <= set(ACCEPTED)


@pytest.mark.unit
def test_menu_draws_every_item_when_ui_is_none():
    """A member with no UI value must still see [F], [R], [D] and [X]. The empty-UI branch
    used to return early, which cut the menu off after [U]."""
    m = _member()
    m["ui"] = None
    out = []
    with um.patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=copy.deepcopy(m))
    text = "\n".join(out)
    for key in ("F", "R", "D"):
        assert f"[{key}]" in text, f"[{key}] missing when ui is None:\n{text}"


@pytest.mark.unit
def test_data_role_is_d_and_x_only_exits_with_q():
    """[D] is the data role. [X] is an exit key alongside [Q], not an option of its own."""
    import inspect
    from bbsengine6.console import member as cm

    src = inspect.getsource(cm._edit)
    assert '"LMECPFDURQX"' in src
    assert 'if ch == "D":' in src
    assert 'elif ch in ("Q", "X"):' in src
    assert 'if ch == "X":' not in src


@pytest.mark.unit
@pytest.mark.parametrize("password", [None, "hunter2-secret"])
def test_password_option_is_always_shown_and_never_reveals_the_value(password):
    """[P] Password is on the edit menu whether or not a password is set, and the value is never
    printed."""
    from unittest.mock import patch
    from bbsengine6.console import member as cm

    m = _member()
    m["password"] = password
    out = []
    with patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=dict(m))
    text = "\n".join(out)
    assert "[P]" in text, text
    assert "hunter2-secret" not in text


@pytest.mark.unit
def test_edit_menu_lists_exit_as_x_and_not_q():
    """The edit menu shows [X] Exit. [Q] still works as a key, but has no entry on the menu."""
    import inspect
    from unittest.mock import patch
    from bbsengine6.console import member as cm

    m = _member()
    out = []
    with patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=dict(m))
    text = "\n".join(out)
    assert "[X]" in text and "Exit" in text, text
    assert "[Q]" not in text, text
    assert '"LMECPFDURQX"' in inspect.getsource(cm._edit)
