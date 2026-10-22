"""getdate-next is optional: bbsengine6 falls back to dateutil without it.

The date input code imports getdate_next lazily and falls back to dateutil,
so getdate-next must not be a core dependency. python-dateutil must stay one,
since it is the fallback.
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _cfg():
    return tomllib.loads(PYPROJECT.read_text())["project"]


@pytest.mark.unit
def test_getdate_next_is_not_a_core_dependency():
    core = _cfg()["dependencies"]
    assert not any(d.lower().startswith("getdate-next") for d in core)


@pytest.mark.unit
def test_getdate_next_is_an_optional_extra():
    extras = _cfg()["optional-dependencies"]
    assert any(d.lower().startswith("getdate-next") for d in extras.get("dates", []))


@pytest.mark.unit
def test_dateutil_remains_a_core_dependency():
    core = _cfg()["dependencies"]
    assert any(d.lower().startswith("python-dateutil") for d in core)
