"""bottombar.init() owns the scroll-region setup. The console calls it, not the deprecated
screen.init shim, so running the console emits no DeprecationWarning.
"""

import warnings
from unittest.mock import patch

import pytest

from bbsengine6 import bottombar


@pytest.mark.unit
def test_bottombar_has_init():
    assert callable(getattr(bottombar, "init", None))


@pytest.mark.unit
def test_init_sets_the_scroll_region_above_the_bottom_margin():
    with patch.object(bottombar, "echo") as echo, \
         patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar.init(None, topmargin=1, bottommargin=1)
    seq = [c.args[0] for c in echo.call_args_list]
    assert any("decstbm" in s or "decstbm:1,23" in s for s in seq) or any("1,23" in s for s in seq), seq


@pytest.mark.unit
def test_console_entry_does_not_call_the_deprecated_screen_init():
    from pathlib import Path
    src = (Path(bottombar.__file__).parent / "console" / "__main__.py").read_text()
    assert "screen.init(" not in src, "console still calls the deprecated screen.init"
    assert "bottombar.init(" in src
