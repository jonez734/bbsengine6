"""No console or log call may print a password value.

Covers io.echo and ttyio.echo, and any variable whose name contains
"password" (including the password itself, not just a label such as
"password is correct").
"""

import pathlib
import re

import bbsengine6

SRC = pathlib.Path(bbsengine6.__file__).parent
TK = SRC.parent / "tk"

# An echo call whose f-string or argument interpolates a password-valued name,
# as {name}, {name=}, or {name!r}. Labels that merely mention the word
# "password" in text (e.g. "password is correct") do not match.
PW_INTERP = re.compile(r"\{\s*(?:plaintext\w*|\w*password\w*|new_password|oldpassword)\s*(?:=|!r|!s|\})")
ECHO = re.compile(r"\b(?:tty)?io\.echo\(|\bttyio\.echo\(")


def _offenders(root: pathlib.Path):
    out = []
    for path in root.rglob("*.py"):
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
            if ECHO.search(code) and PW_INTERP.search(code):
                out.append(f"{path.relative_to(root.parent)}:{n}: {line.strip()}")
    return out


def test_no_echo_prints_a_password_value_in_bbsengine6():
    assert _offenders(SRC) == []


def test_no_echo_prints_a_password_value_in_tk():
    assert _offenders(TK) == []
