"""Debug output must never print a password. redact() masks secret keys; member and database use it."""

from pathlib import Path

import pytest

from bbsengine6.redact import redact

SRC = Path(__file__).parents[1] / "src" / "bbsengine6"


@pytest.mark.unit
def test_password_is_masked_and_the_rest_is_kept():
    out = redact({"moniker": "jam", "password": "$2b$06$SECRET", "flags": {"SYSOP": {"value": True}}})
    assert out == {"moniker": "jam", "password": "***", "flags": {"SYSOP": {"value": True}}}


@pytest.mark.unit
def test_mixed_case_and_nested_secret_keys_are_masked():
    out = redact({"Password": "x", "inner": [{"passwordhash": "y"}]})
    assert out == {"Password": "***", "inner": [{"passwordhash": "***"}]}


@pytest.mark.unit
def test_redact_does_not_change_the_original():
    original = {"password": "keep-me"}
    redact(original)
    assert original == {"password": "keep-me"}


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,needles",
    [
        ("member/lib.py", ("member={redact(member)}", "rec={redact(rec)}")),
        ("database.py", ("kwargs={redact(kwargs)}",)),
    ],
)
def test_secret_bearing_echoes_use_redact(path, needles):
    src = (SRC / path).read_text()
    for needle in needles:
        assert needle in src, f"{needle} missing from {path}"


@pytest.mark.unit
def test_no_raw_member_dict_is_printed_in_debug():
    text = (SRC / "member" / "lib.py").read_text()
    for raw in ("{member=}", "{rec=}"):
        assert raw not in text, f"raw {raw} still printed"
