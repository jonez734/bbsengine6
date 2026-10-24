"""bbsengine6's `venv` target installs into a local venv and never touches a remote host.

deploy bed.venv depends on bbsengine6.venv. The recipe may build the wheel and pip-install
it locally, and must not run rsync, ssh, scp, or name merlin/falcon.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]  # bbsengine6/
MAKEFILE = ROOT / "Makefile"

REMOTE = re.compile(r"\b(rsync|ssh|scp|merlin|falcon)\b")


def _recipe(name: str) -> str:
    """The recipe lines for make target `name` (up to the next target or blank-line gap)."""
    lines = MAKEFILE.read_text().splitlines()
    out, active = [], False
    for line in lines:
        if re.match(rf"^{re.escape(name)}\s*:", line):
            active = True
            out.append(line)
            continue
        if active:
            if line.startswith("\t") or line.startswith("#") or line.strip() == "":
                if line.strip() == "" and out and not out[-1].startswith("\t"):
                    break
                out.append(line)
            else:
                break
    return "\n".join(out)


@pytest.mark.unit
def test_venv_target_exists():
    assert re.search(r"^venv\s*:", MAKEFILE.read_text(), re.MULTILINE)


@pytest.mark.unit
def test_venv_recipe_has_no_remote_commands():
    body = _recipe("venv")
    assert body, "venv recipe not found"
    hits = [l for l in body.splitlines() if REMOTE.search(l) and not l.lstrip().startswith("#")]
    assert hits == [], hits


@pytest.mark.unit
def test_venv_recipe_builds_and_installs_locally():
    body = _recipe("venv")
    assert re.search(r'bin/pip"?\s+install', body), body
    assert "-m build" in body
