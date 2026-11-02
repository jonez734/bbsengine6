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


def test_apply_plan_refuses_missing_path_before_any_grant(tmp_path, monkeypatch):
    """A later missing path refuses before an earlier path is granted."""
    grant = []
    monkeypatch.setattr(acl, "grant_acl", lambda *a, **k: grant.append(a))
    plan = [
        acl.AclEntry(str(tmp_path), "g", "x"),
        acl.AclEntry(str(tmp_path / "missing"), "g", "x"),
    ]
    with pytest.raises(FileNotFoundError, match="missing"):
        acl.apply_plan(plan)
    assert grant == []


def test_apply_plan_grants_each_entry_in_order(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(acl, "grant_acl", lambda path, group, perms, default=False: calls.append((path, group, perms, default)))
    plan = [
        acl.AclEntry(str(tmp_path), "g1", "x"),
        acl.AclEntry(str(tmp_path), "g2", "rwX", default=True),
    ]
    acl.apply_plan(plan)
    assert calls == [(str(tmp_path), "g1", "x", False), (str(tmp_path), "g2", "rwX", True)]


def test_check_plan_pairs_each_entry_with_its_result(tmp_path, monkeypatch):
    monkeypatch.setattr(acl, "check_acl", lambda path, group, want: path.endswith("ok"))
    plan = [acl.AclEntry("/x/ok", "g", "x"), acl.AclEntry("/x/no", "g", "x")]
    assert acl.check_plan(plan) == [(plan[0], True), (plan[1], False)]
