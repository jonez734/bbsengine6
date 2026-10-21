"""schemaexists sees every schema, not only the ones the current role can use.

information_schema.schemata lists only schemas the connecting role has privileges
on. A role without privileges on the casino schema saw it as absent, re-ran its
creation, and failed. pg_namespace lists every schema.
"""

import inspect

from bbsengine6 import database


def test_schemaexists_queries_pg_namespace():
    src = inspect.getsource(database.schemaexists)
    # Look at the SQL string only; the comment mentions the old view on purpose.
    sql_lines = [ln for ln in src.splitlines() if "FROM" in ln.upper() and not ln.strip().startswith("#")]
    assert any("pg_namespace" in ln for ln in sql_lines), "schemaexists must query pg_namespace"
    assert not any("information_schema.schemata" in ln for ln in sql_lines), \
        "information_schema.schemata hides schemas from roles without privileges"
