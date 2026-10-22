"""Plaintext passwords must never be written to the console or logs."""

import pathlib
import re

import bbsengine6

SRC = pathlib.Path(bbsengine6.__file__).parent


def _lines_with_echo(path: pathlib.Path):
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if re.search(r"io\.echo\(", line) and re.search(r"plaintext", line, re.IGNORECASE):
            yield n, line.strip()


def test_no_io_echo_prints_a_plaintext_password():
    offenders = []
    for path in SRC.rglob("*.py"):
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        offenders += [f"{path.relative_to(SRC)}:{n}: {l}" for n, l in _lines_with_echo(path)]
    assert offenders == [], "\n".join(offenders)
