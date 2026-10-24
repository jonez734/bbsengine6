"""engine.blurb, engine.site and siteauth depend on the blurb table group, which startup does not
build. They must stay out of classlist and out of the drop file until that group is registered.
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkclasses

SQL = Path(pgrole.__file__).parent / "sql"


@pytest.mark.unit
@pytest.mark.parametrize("name", ["engine.blurb", "engine.site", "siteauth"])
def test_blurb_dependent_view_is_not_in_classlist(name):
    assert name not in {cls for cls, _ in checkclasses.classlist}


@pytest.mark.unit
@pytest.mark.parametrize("name", ["engine.blurb", "engine.site", "siteauth"])
def test_blurb_dependent_view_is_not_dropped(name):
    text = (SQL / "drop_views_for_recreate.sql").read_text()
    assert f"drop view if exists {name};" not in text.lower(), name
