"""Message reads on bed's connection go through the zoid6-owned functions.

Two regressions this pins:
1. The pending and unread reads call engine.bed_list_pending_page and
   engine.bed_count_unread, not the tables (bed has no table privileges).
2. The unread path does not use information_schema to decide whether the
   table exists. bed cannot see the message tables there, so the probe would
   report "missing" and return 0 even when messages exist.
"""

import io
import re
import tokenize
from pathlib import Path

import bbsengine6.message.dal.messages as dal_messages

SRC = Path(dal_messages.__file__).read_text()


def _function_body(name: str) -> str:
    """Source of ``name`` with comments removed (code only).

    Uses tokenize so string literals containing '#' (like SQL) are kept.
    """
    m = re.search(rf"def {name}\(.*?(?=\ndef |\Z)", SRC, re.DOTALL)
    assert m, f"{name} not found"
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(m.group(0)).readline):
        if tok.type == tokenize.COMMENT:
            continue
        out.append(tok)
    return tokenize.untokenize(out)


def test_list_pending_page_calls_bed_function():
    body = _function_body("list_pending_page")
    assert "engine.bed_list_pending_page" in body
    assert "FROM engine.__message m" not in body


def test_count_unread_calls_bed_function():
    body = _function_body("count_unread_for_recipient")
    assert "engine.bed_count_unread" in body
    assert "information_schema" not in body


def test_count_unread_does_not_probe_table_existence():
    body = _function_body("count_unread_for_recipient")
    assert "table_exists" not in body
