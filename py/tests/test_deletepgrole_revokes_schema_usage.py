# bbsengine6/py/tests/test_deletepgrole_revokes_schema_usage.py
# engine.deletepgrole must be able to drop a member's data role. The role holds USAGE on the engine
# schema (granted by pgrole step 4), which blocks DROP ROLE. The function must therefore revoke that
# grant itself. It is owned by zoid6, so it must be SECURITY DEFINER, or the revoke runs as the
# caller and PostgreSQL silently ignores it.
import re
from pathlib import Path

import pytest

SQL = Path(__file__).resolve().parents[1] / "src" / "bbsengine6" / "sql" / "createrol.sql"


def _deletepgrole_block() -> str:
    text = SQL.read_text()
    start = text.index("CREATE OR REPLACE FUNCTION engine.deletepgrole")
    end = text.index("grant execute on function engine.deletepgrole", start)
    return text[start:end]


@pytest.mark.unit
def test_deletepgrole_is_security_definer():
    assert re.search(r"\bSECURITY\s+DEFINER\b", _deletepgrole_block(), re.I), (
        "deletepgrole must run as its zoid6 owner so the schema revoke takes effect"
    )


@pytest.mark.unit
def test_deletepgrole_revokes_the_engine_schema_usage_before_dropping_the_role():
    block = _deletepgrole_block()
    revoke = re.search(r"REVOKE\s+USAGE\s+ON\s+SCHEMA\s+engine\s+FROM", block, re.I)
    drop = block.find("DROP ROLE")
    assert revoke is not None, "deletepgrole must revoke the role's USAGE on schema engine"
    assert revoke.start() < drop, "the revoke must come before the DROP ROLE"


@pytest.mark.unit
def test_deletepgrole_still_removes_the_tracking_row():
    assert "DELETE FROM engine.pgrole" in _deletepgrole_block()
