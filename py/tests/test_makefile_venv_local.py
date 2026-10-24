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


@pytest.mark.unit
def test_venv_recipe_installs_build_before_using_it():
    """`python -m build` runs inside the target venv, which may not have `build` yet
    (a fresh venv, or one created for the bed service). Install it first."""
    body = _recipe("venv")
    install_build = re.search(r'bin/pip"?\s+install[^\n]*\bbuild\b', body)
    use_build = body.find("-m build")
    assert install_build, body
    assert install_build.start() < use_build, body


@pytest.mark.unit
def test_venv_recipe_installs_only_the_wheel_it_just_built():
    """Stale wheels from earlier builds conflict, so the install must read only this build's output."""
    body = _recipe("venv")
    install = re.search(r'bin/pip"?\s+install[^\n]*\$\$"?wheels"?/\*\.whl', body)
    assert install, body
    assert "mktemp" in body and body.index("mktemp") < install.start(), body


@pytest.mark.unit
def test_venv_recipe_builds_into_a_fresh_temp_dir():
    """A root-owned py/dist left by an earlier sudo run must not break the venv deploy.

    The recipe builds into a new temp directory and installs from it, so no shared
    output directory has to be deleted or written to.
    """
    body = _recipe("venv")
    assert "mktemp" in body, body
    assert "py/dist" not in body, body
    assert "rm -rf py/dist" not in body, body
