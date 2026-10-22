"""Docs that show member API examples use the current moniker API."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

DOCS = [
    ROOT / "bbsengine6" / "handbook" / "specs" / "console.md",
    ROOT / "specs" / "PROJECT_ANALYSIS.md",
    ROOT / "mistermcfeely" / "specs" / "PROJECT_ANALYSIS.md",
]


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_doc_does_not_show_removed_getcurrentid_as_live(doc):
    assert "member.getcurrentid(" not in doc.read_text(), doc.name
