"""module.run hands a module's main the caller's configured args when no argv is given.

Regression: bed parses --databasename and applies the config, then starts
bbsengine6's startup. module.run re-parsed an empty argv through the stage
parser, which restored the parser default (NEEDINFO) and dropped the caller's
database name, so the pre-flight connected to the wrong target.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import module


@pytest.mark.unit
def test_empty_argv_keeps_callers_database_name():
    caller = argparse.Namespace(databasename="zoid6", debug=False)
    stage_parser = argparse.ArgumentParser()
    stage_parser.add_argument("--databasename", default="NEEDINFO")

    seen = {}

    def fake_main(a, **kw):
        seen["databasename"] = a.databasename
        return True

    fake_mod = MagicMock()
    fake_mod.buildargs.return_value = stage_parser
    fake_mod.main = fake_main
    fake_mod.init.return_value = True

    with patch.object(module, "get", return_value=fake_mod), \
         patch.object(module, "check", return_value=True), \
         patch.object(module, "get_module", return_value=None):
        module.run(caller, "stage_zero", argv=[])

    assert seen["databasename"] == "zoid6", seen
