"""bbsengine6 must not list itself in its own dependencies (pip cannot resolve a self-requirement)."""

import pathlib
import tomllib

import pytest

PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"


@pytest.mark.unit
def test_bbsengine6_does_not_depend_on_itself():
    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    names = {d.split("[")[0].split(">")[0].split("<")[0].split("=")[0].split(";")[0].strip().lower() for d in deps}
    assert "bbsengine6" not in names, deps
