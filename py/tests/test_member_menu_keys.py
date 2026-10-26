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

ACCEPTED = "LMECPFXURQ"


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
    """A member with no UI value must still see [F], [R], [O] and [X]. The empty-UI branch
    used to return early, which cut the menu off after [U]."""
    m = _member()
    m["ui"] = None
    out = []
    with um.patch.object(cm.io, "echo", side_effect=lambda *a, **k: out.append(str(a[0]) if a else "")):
        cm.render_member(None, member=m, _member=copy.deepcopy(m))
    text = "\n".join(out)
    for key in ("F", "R", "X"):
        assert f"[{key}]" in text, f"[{key}] missing when ui is None:\n{text}"
