"""Tests for bbsengine6.acl. No setfacl runs against real paths.

grant_acl is exercised only for its refusal on a missing path. check_acl and
parse_getfacl are tested on sample getfacl text, so these tests need no ACL
support on the host.
"""

import pytest

from bbsengine6 import acl


SAMPLE_GETFACL = """\
# file: /home/zoid6/venv
# owner: zoid6
# group: zoid6
user::rwx
group::r-x
group:opencode:rwx
mask::rwx
other::r-x
default:user::rwx
default:group::r-x
default:group:opencode:rwx
default:mask::rwx
default:other::r-x
"""

SAMPLE_EFFECTIVE = """\
# file: /home/zoid6/dist-wheels
# owner: zoid6
# group: zoid6
user::rwx
group::r-x
group:opencode:rwx\t#effective:r-x
mask::r-x
other::r-x
"""


def test_grant_acl_refuses_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        acl.grant_acl(str(missing), "opencode", "rwX")


def test_grant_acl_refuses_missing_path_before_running_setfacl(tmp_path, monkeypatch):
    """The path check happens before setfacl is looked up or run."""
    called = []

    def fake_run(argv):
        called.append(argv)
        raise AssertionError("setfacl must not run for a missing path")

    monkeypatch.setattr(acl, "_run", fake_run)
    with pytest.raises(FileNotFoundError):
        acl.grant_acl(str(tmp_path / "missing"), "opencode", "x")
    assert called == []


def test_parse_getfacl_returns_raw_entry():
    assert acl.parse_getfacl(SAMPLE_GETFACL, "opencode") == "rwx"


def test_parse_getfacl_prefers_effective_value():
    assert acl.parse_getfacl(SAMPLE_EFFECTIVE, "opencode") == "r-x"


def test_parse_getfacl_ignores_default_entries_for_named_group():
    text = "group:opencode:r--\ndefault:group:opencode:rwx\n"
    assert acl.parse_getfacl(text, "opencode") == "r--"


def test_parse_getfacl_missing_group_returns_none():
    assert acl.parse_getfacl(SAMPLE_GETFACL, "nobody") is None


def test_parse_getfacl_does_not_match_owning_group():
    """'group::' is the owning group entry, not a named group called ''."""
    assert acl.parse_getfacl("group::r-x\n", "") is None


@pytest.mark.parametrize(
    "effective,want,expected",
    [
        ("rwx", "rwX", True),
        ("rwx", "x", True),
        ("r-x", "x", True),
        ("r-x", "rwX", False),
        ("r--", "x", False),
        (None, "x", False),
    ],
)
def test_has_all(effective, want, expected):
    assert acl._has_all(effective, want) is expected


def test_check_acl_missing_path_is_false(tmp_path):
    assert acl.check_acl(str(tmp_path / "missing"), "opencode", "x") is False


def test_check_acl_uses_getfacl_text(tmp_path, monkeypatch):
    """check_acl reads getfacl output; the path exists, the tool is faked."""
    monkeypatch.setattr(acl, "getfacl_text", lambda path: SAMPLE_EFFECTIVE)
    assert acl.check_acl(str(tmp_path), "opencode", "x") is True
    assert acl.check_acl(str(tmp_path), "opencode", "rwX") is False


def test_check_acl_getfacl_failure_is_false(tmp_path, monkeypatch):
    def boom(path):
        raise RuntimeError("getfacl failed")

    monkeypatch.setattr(acl, "getfacl_text", boom)
    assert acl.check_acl(str(tmp_path), "opencode", "x") is False


def test_acl_plan_matches_expected_entries():
    plan = acl.acl_plan()
    assert plan == [
        acl.AclEntry("/home/zoid6", "opencode", "x"),
        acl.AclEntry("/home/zoid6/venv", "opencode", "rwX"),
        acl.AclEntry("/home/zoid6/venv", "opencode", "rwX", default=True),
        acl.AclEntry("/home/zoid6/dist-wheels", "opencode", "rwX"),
        acl.AclEntry("/home/zoid6/dist-wheels", "opencode", "rwX", default=True),
    ]


def test_acl_plan_grants_only_traverse_on_home():
    home = [e for e in acl.acl_plan() if e.path == "/home/zoid6"]
    assert home == [acl.AclEntry("/home/zoid6", "opencode", "x")]


def test_acl_plan_has_no_zoid6_group_grant():
    """Grants go to the opencode group only, never to zoid6 (see plan)."""
    assert all(e.group == "opencode" for e in acl.acl_plan())
