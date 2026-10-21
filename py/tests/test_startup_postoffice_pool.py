"""bbsengine6 startup hands postoffice a pool.

Regression: postoffice.startup_main returns False ("pool is None") when called
with neither conn nor pool, and bed startup then failed. The call must pass the
same target pool the stage_one step uses.
"""

import importlib
import inspect

import pytest

startup_main = importlib.import_module("bbsengine6.startup.main")


@pytest.mark.unit
def test_postoffice_call_passes_target_pool():
    src = inspect.getsource(startup_main.main)
    call = [line for line in src.splitlines() if 'package="postoffice"' in line]
    assert call, "postoffice runmodule call not found"
    assert "pool=target_pool" in call[0]
