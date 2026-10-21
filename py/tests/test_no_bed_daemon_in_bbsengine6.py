"""bbsengine6 must not ship the bed daemon. The daemon lives in the bed project.

bbsengine6 runs without bed. A daemon module inside the library is the
wrong direction, so it is removed from this package.
"""

import importlib.util
from pathlib import Path

import bbsengine6


def test_bed_daemon_module_absent():
    assert not (Path(bbsengine6.__file__).parent / "bed.py").exists()


def test_bed_daemon_module_not_importable():
    assert importlib.util.find_spec("bbsengine6.bed") is None
