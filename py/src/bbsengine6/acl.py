"""
POSIX ACL helpers for the zoid6 account's install paths.

Public surface:

  acl_plan() -> list[AclEntry]
      The ACL entries zoid6 needs: traverse on /home/zoid6, and group write
      (plus default ACLs) on the venv and dist-wheels. Pure data; no I/O.

  grant_acl(path, group, perms, default=False) -> str
      Runs ``setfacl -m`` (``-d`` for a default ACL) and returns the resulting
      ``getfacl`` text. Refuses a missing path. Re-running is safe: ``setfacl
      -m`` replaces an existing entry for the same group.

  check_acl(path, group, want) -> bool
      Read-only. Reads ``getfacl`` and reports whether the effective permissions
      for ``group:<group>`` include ``want`` (for example ``"x"`` or ``"rwx"``).

  parse_getfacl(text, group) -> str | None
      Pure parser for ``getfacl`` output. Returns the effective permission string
      for ``group`` ("rwx", "r-x", ...), or None if the group has no entry.

``setfacl`` and ``getfacl`` are only invoked from grant_acl and check_acl, never
at import time, so importing this module is safe on any host.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Sequence

ZOID6_HOME = "/home/zoid6"
ZOID6_VENV = "/home/zoid6/venv"
ZOID6_DIST_WHEELS = "/home/zoid6/dist-wheels"
ACL_GROUP = "opencode"


@dataclass(frozen=True)
class AclEntry:
    """One ACL to grant: ``group`` gets ``perms`` on ``path``.

    ``default`` also sets a default ACL, so files created later inherit it.
    """

    path: str
    group: str
    perms: str
    default: bool = False


def acl_plan() -> list[AclEntry]:
    """The ACL entries for the zoid6 account, in the order they are applied.

    ``/home/zoid6`` only needs traverse (``x``) so the group can reach the
    venv and dist-wheels without listing the rest of the home directory.
    """
    return [
        AclEntry(ZOID6_HOME, ACL_GROUP, "x"),
        AclEntry(ZOID6_VENV, ACL_GROUP, "rwX"),
        AclEntry(ZOID6_VENV, ACL_GROUP, "rwX", default=True),
        AclEntry(ZOID6_DIST_WHEELS, ACL_GROUP, "rwX"),
        AclEntry(ZOID6_DIST_WHEELS, ACL_GROUP, "rwX", default=True),
    ]


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH (install the acl package)")
    return path


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), capture_output=True, text=True, check=False)


def getfacl_text(path: str) -> str:
    """Return ``getfacl`` output for ``path``. Raises RuntimeError on failure."""
    tool = _require_tool("getfacl")
    proc = _run([tool, "-p", path])
    if proc.returncode != 0:
        raise RuntimeError(f"getfacl {path} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_getfacl(text: str, group: str) -> str | None:
    """Return the effective permissions for ``group`` from ``getfacl`` text.

    ``getfacl`` prints named-group entries as ``group:<name>:<perms>`` and, when
    a mask is set, the effective value after ``#effective:``. The effective value
    is preferred; the raw entry is used if no effective annotation is present.
    Returns None when the group has no named entry.
    """
    raw: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("group:") and not line.startswith("group::"):
            _, name, rest = (line.split(":", 2) + [""])[:3]
            if name != group:
                continue
            # rest may be "r-x" or "r-x\t#effective:r--"
            perms, _, effective = rest.partition("\t")
            if effective.startswith("#effective:"):
                return effective[len("#effective:"):].strip()
            raw = perms.strip()
    return raw


def grant_acl(path: str, group: str, perms: str, default: bool = False) -> str:
    """Grant ``group`` ``perms`` on ``path`` with ``setfacl -m``.

    With ``default=True`` the grant is a default ACL (``setfacl -d -m``), so
    files created later inherit it. Returns the resulting ``getfacl`` text.
    Raises FileNotFoundError for a missing path and RuntimeError if setfacl
    fails.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"grant_acl: {path} does not exist")
    tool = _require_tool("setfacl")
    spec = f"g:{group}:{perms}"
    argv = [tool]
    if default:
        argv.append("-d")
    argv += ["-m", spec, path]
    proc = _run(argv)
    if proc.returncode != 0:
        raise RuntimeError(f"setfacl {spec} {path} failed: {proc.stderr.strip()}")
    return getfacl_text(path)


def _has_all(effective: str | None, want: str) -> bool:
    if effective is None:
        return False
    # "x" must be present in the effective string at the matching position.
    # Compare by character so "rwx" satisfies "rwX" and "x" alike.
    for ch in want.lower():
        if ch == "-":
            continue
        if ch not in effective.lower():
            return False
    return True


def check_acl(path: str, group: str, want: str) -> bool:
    """Read-only. True when ``group``'s effective permissions on ``path`` cover ``want``.

    ``want`` is a permission string such as ``"x"`` or ``"rwX"``. Case is
    ignored, since ``X`` (execute on directories) is treated as ``x`` here.
    Returns False when the path is missing or ``getfacl`` fails.
    """
    if not os.path.exists(path):
        return False
    try:
        text = getfacl_text(path)
    except RuntimeError:
        return False
    return _has_all(parse_getfacl(text, group), want)
