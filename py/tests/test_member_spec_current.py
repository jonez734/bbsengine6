"""handbook/specs/member.md describes the current member API, not the removed id-based one."""

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[2] / "handbook" / "specs" / "member.md"


def _text() -> str:
    return SPEC.read_text()


def test_spec_does_not_list_getcurrentid_as_a_live_signature():
    assert not re.search(r"^getcurrentid\(args", _text(), re.MULTILINE)


def test_spec_does_not_list_getbyid_as_a_live_signature():
    assert not re.search(r"^getbyid\(args", _text(), re.MULTILINE)


def test_spec_documents_both_removals():
    t = _text()
    assert "getcurrentid" in t and "raises" in t.lower()
    assert "getbyid" in t and "getbymoniker" in t


def test_spec_documents_getbalance_and_its_order():
    t = _text()
    assert "getbalance" in t
    assert "bank" in t.lower() and "credits" in t


def test_spec_no_longer_lists_id_in_allowed_columns():
    assert "id, loginid" not in _text()
