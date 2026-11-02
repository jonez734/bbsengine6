"""
Object-existence checks against a JSON manifest.

A manifest lists the database objects one project's install creates. This
module validates it and reports, read-only, whether those objects exist.

Manifest format (``sql/objects.json`` in each project)::

    {
      "schema_version": 1,
      "project": "bed",
      "objects": [
        {"kind": "role", "name": "bed_obj"},
        {"kind": "table", "name": "engine.__bed_token"},
        {"kind": "function", "name": "engine.bed_bank_op", "args": "bytea, text, jsonb"}
      ]
    }

Kinds: role, schema, table, view, sequence, function. Names of schema-qualified
kinds are ``schema.name``; a role or schema name is bare. A function needs
``args`` so an overload is matched exactly.

Public surface:

  load_manifest(path_or_dict) -> Manifest      validates; raises ManifestError
  check_objects(args, manifest, conn=...) -> Report
      status is "installed" (all present), "partial" (some present), or
      "not installed" (none present). ``missing`` lists what is absent.

check_objects never runs DDL and never raises on a missing object.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bbsengine6 import database, io

SCHEMA_VERSION = 1
KINDS = frozenset({"role", "schema", "table", "view", "sequence", "function"})
STATUS_INSTALLED = "installed"
STATUS_PARTIAL = "partial"
STATUS_NOT_INSTALLED = "not installed"

_IDENT = r"[a-z_][a-z0-9_]*"
_NAME_RE = re.compile(rf"^{_IDENT}(\.{_IDENT})?$")
_BARE_RE = re.compile(rf"^{_IDENT}$")
_ARGS_RE = re.compile(r"^[A-Za-z0-9_\[\], ]*$")


class ManifestError(ValueError):
    """Raised for a manifest that does not validate."""


@dataclass(frozen=True)
class ObjectRef:
    kind: str
    name: str
    args: str | None = None

    def label(self) -> str:
        if self.kind == "function":
            return f"function {self.name}({self.args})"
        return f"{self.kind} {self.name}"


@dataclass(frozen=True)
class Manifest:
    project: str
    objects: tuple[ObjectRef, ...]


@dataclass
class Report:
    project: str
    status: str
    present: list[ObjectRef] = field(default_factory=list)
    missing: list[ObjectRef] = field(default_factory=list)


def _check_entry(index: int, entry: Any) -> ObjectRef:
    where = f"objects[{index}]"
    if not isinstance(entry, dict):
        raise ManifestError(f"{where} must be an object")
    kind = entry.get("kind")
    name = entry.get("name")
    if kind not in KINDS:
        raise ManifestError(f"{where}.kind {kind!r} is not one of {sorted(KINDS)}")
    if not isinstance(name, str):
        raise ManifestError(f"{where}.name must be a string")
    if kind in ("role", "schema"):
        if not _BARE_RE.match(name):
            raise ManifestError(f"{where}.name {name!r} is not a bare identifier")
    elif not _NAME_RE.match(name):
        raise ManifestError(f"{where}.name {name!r} must be name or schema.name")
    args = entry.get("args")
    if kind == "function":
        if "." not in name:
            raise ManifestError(f"{where}.name {name!r} must be schema-qualified (schema.function)")
        if not isinstance(args, str):
            raise ManifestError(f"{where}: a function needs an 'args' string (exact overload)")
        if not _ARGS_RE.match(args):
            raise ManifestError(f"{where}.args {args!r} has characters not allowed in a signature")
    elif args is not None:
        raise ManifestError(f"{where}: 'args' is only valid for functions")
    return ObjectRef(kind=kind, name=name, args=args)


def load_manifest(source: Any) -> Manifest:
    """Validate a manifest given as a file path or an already-parsed dict.

    Raises ManifestError on any violation: wrong schema_version, unknown kind,
    bad name, a function without args, or a duplicate object.
    """
    if isinstance(source, (str, Path)):
        try:
            data = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read manifest {source}: {exc}") from exc
    else:
        data = source
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(
            f"schema_version must be {SCHEMA_VERSION}, got {data.get('schema_version')!r}"
        )
    project = data.get("project")
    if not isinstance(project, str) or not project:
        raise ManifestError("project must be a non-empty string")
    raw = data.get("objects")
    if not isinstance(raw, list) or not raw:
        raise ManifestError("objects must be a non-empty list")
    objects = tuple(_check_entry(i, e) for i, e in enumerate(raw))
    seen: set[ObjectRef] = set()
    for obj in objects:
        if obj in seen:
            raise ManifestError(f"duplicate entry: {obj.label()}")
        seen.add(obj)
    return Manifest(project=project, objects=objects)


def _exists(cur, obj: ObjectRef) -> bool:
    """True when the catalog has ``obj``. Every query returns one row with ``present``."""
    if obj.kind == "role":
        sql = "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s) AS present"
        params: tuple = (obj.name,)
    elif obj.kind == "schema":
        sql = "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s) AS present"
        params = (obj.name,)
    elif obj.kind in ("table", "view", "sequence"):
        sql = "SELECT to_regclass(%s) IS NOT NULL AS present"
        params = (obj.name,)
    else:  # function: exact signature, so overloads are distinguished
        sql = "SELECT to_regprocedure(%s) IS NOT NULL AS present"
        params = (f"{obj.name}({obj.args})",)
    cur.execute(sql, params)
    row = cur.fetchone()
    # Only a real boolean from the catalog counts as present. Anything else (no row, an
    # unexpected shape, a test double) is treated as absent: a gate must not pass on
    # a value it did not actually read.
    if isinstance(row, dict):
        value = row.get("present")
    elif isinstance(row, (tuple, list)) and row:
        value = row[0]
    else:
        return False
    return value is True


def _status(present: int, total: int) -> str:
    if present == total:
        return STATUS_INSTALLED
    if present == 0:
        return STATUS_NOT_INSTALLED
    return STATUS_PARTIAL


def check_objects(args: Any, manifest: Manifest, **kwargs: Any) -> Report:
    """Report which manifest objects exist. Read-only.

    Pass ``conn=`` (a connection) or ``pool=`` (a pool). Returns a Report whose
    ``status`` is installed, partial, or not installed.
    """
    conn = kwargs.get("conn")
    pool = kwargs.get("pool")
    present: list[ObjectRef] = []
    missing: list[ObjectRef] = []

    def _work(c):
        with database.cursor(conn=c) as cur:
            for obj in manifest.objects:
                (present if _exists(cur, obj) else missing).append(obj)

    if conn is not None:
        _work(conn)
    elif pool is not None:
        with database.connect(args, pool=pool) as c:
            _work(c)
    else:
        raise ValueError("check_objects needs conn= or pool=")

    report = Report(
        project=manifest.project,
        status=_status(len(present), len(manifest.objects)),
        present=present,
        missing=missing,
    )
    io.echo(f"objects {manifest.project}: {report.status} ({len(present)}/{len(manifest.objects)})", level="debug")
    return report
