"""Only the bed project owns the ``bed`` console script.

Both bbsengine6 and bed declared a ``bed`` command. Installing both into one
venv let bbsengine6's win, so the zoid6 unit ran a different server with a
different argument set. bbsengine6 is a library and must not claim ``bed``.
"""

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_bbsengine6_does_not_declare_bed_script():
    scripts = tomllib.loads(PYPROJECT.read_text(encoding="utf-8")).get("project", {}).get("scripts", {})
    assert "bed" not in scripts, f"bbsengine6 must not own the bed command: {scripts}"
