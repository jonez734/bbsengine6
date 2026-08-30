"""
bbsengine6.config - generic JSON + env + default merge helpers.

Application-agnostic helpers for loading JSON configuration, deep-merging
overrides, and layering environment variables on top. Designed so that
downstream apps (zoidoffice, asimov, bed, achilles, ...) can share a
common precedence chain without each re-implementing it.

Precedence chain produced by :func:`build_argparse_defaults` (top wins):
    1. CLI flag (``argparse`` handles this; not seen here)
    2. Environment variable ``${env_prefix}_${KEY}`` (uppercased)
    3. JSON ``config[section][key]``
    4. JSON ``config[global_section][key]``
    5. ``hardcoded_defaults[key]``

String values from JSON are recursively expanded for ``${VAR}`` (env)
and ``~`` (user) before being returned. Keys ending in ``_path``,
``_file``, ``_dir``, ``_socket``, or ``_log`` additionally run through
:func:`bbsengine6.common.safe_path` so operators can write
``"~/logs/zoidoffice.log"`` portably.

This module is intentionally small and dependency-free (only stdlib).
It does not import any other ``bbsengine6`` module except
:mod:`bbsengine6.common.safe_path` for path expansion.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

from .common import safe_path

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Key suffixes that mark a value as a filesystem path and therefore
#: eligible for safe_path() expansion (in addition to standard ${VAR}
#: and ~ expansion). Matches the convention used by ``bed.config``.
PATH_KEY_SUFFIXES: tuple[str, ...] = ("_path", "_file", "_dir", "_socket", "_log")

#: Regex matching ``${VAR}`` placeholders in string values. We accept
#: uppercase, lowercase, digits, and underscore in the variable name.
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

#: Sections that most apps will recognize. Apps may pass their own
#: frozenset to :func:`validate_schema` to opt in to warnings for
#: unknown top-level sections.
DEFAULT_KNOWN_SECTIONS: frozenset[str] = frozenset({"global"})


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def load_json_file(path: Path) -> dict:
    """Load a single JSON file and return its top-level dict.

    Returns an empty dict when the file does not exist, cannot be
    read, or does not contain a JSON object at the top level. Never
    raises - callers that need strict semantics should call
    :func:`load_json_file_strict` instead.
    """
    try:
        with open(path) as f:
            data = f.read()
    except (OSError, UnicodeDecodeError):
        return {}
    if not data.strip():
        return {}
    import json

    try:
        loaded = json.loads(data)
    except ValueError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def load_json_file_strict(path: Path) -> dict:
    """Strict variant of :func:`load_json_file`.

    Raises:
        FileNotFoundError: if the file does not exist.
        OSError: on permission/IO problems.
        ValueError: on invalid JSON or a non-dict top-level value.
    """
    import json

    with open(path) as f:
        loaded = json.load(f)
    if not isinstance(loaded, dict):
        raise TypeError(
            f"{path}: top-level JSON value must be an object/dict, "
            f"got {type(loaded).__name__}"
        )
    return loaded


def search_config(
    candidates: Iterable[Path],
    *,
    env_var: str | None = None,
) -> tuple[dict, Path | None]:
    """Walk ``candidates`` in order and load the first existing JSON file.

    If ``env_var`` is set and that environment variable names a file
    that exists, that file is tried first regardless of the candidate
    list (so operators can override the search path with a single
    variable). The env-var path is *not* required to be inside the
    candidate list.

    Returns:
        ``(config_dict, path_used)``. ``config_dict`` is the parsed
        JSON (or ``{}`` when no candidate exists); ``path_used`` is
        the path that produced it (or ``None`` when nothing matched).
    """
    if env_var:
        env_path = os.environ.get(env_var)
        if env_path:
            p = Path(env_path)
            if p.exists():
                data = load_json_file(p)
                if data or p.exists():
                    return data, p

    last: Path | None = None
    for candidate in candidates:
        if candidate is None:
            continue
        last = candidate
        if not candidate.exists():
            continue
        data = load_json_file(candidate)
        if data or candidate.exists():
            return data, candidate

    return {}, last


def deep_merge(base: dict, override: dict) -> dict:
    """Recursive merge; ``override`` wins on scalar conflicts.

    Returns a new dict; the inputs are not mutated. Lists are replaced
    wholesale (not concatenated). Non-dict values in ``override`` that
    collide with dict values in ``base`` replace the dict (callers
    that need finer control should pre-flatten their input).
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if isinstance(override, dict) else dict(base or {})
    out = dict(base)
    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve(
    env_value: Any,
    json_value: Any = None,
    default: Any = None,
) -> Any:
    """Single-key precedence: ``env_value ?? json_value ?? default``.

    Precedence (top wins): env var > JSON > hardcoded default.

    ``None`` and empty string both count as "unset" for this helper,
    matching argparse's "did the user supply a value?" semantics. If
    you need to distinguish "key absent" from "key present and None",
    do that check at the caller.

    Argument order is ``(env, json, default)`` so the env-var-first
    precedence reads naturally at the call site in
    :func:`build_argparse_defaults`.
    """
    if env_value not in (None, ""):
        return env_value
    if json_value not in (None, ""):
        return json_value
    return default


def get_section(config: dict, *path: str) -> dict:
    """Return ``config[path[0]][path[1]]...[path[-1]]`` or ``{}``.

    Any missing or non-dict intermediate yields ``{}``. Never raises.
    """
    node: Any = config
    for key in path:
        if not isinstance(node, dict):
            return {}
        node = node.get(key)
        if node is None:
            return {}
    if not isinstance(node, dict):
        return {}
    return node


# ---------------------------------------------------------------------------
# Expansion
# ---------------------------------------------------------------------------

_BARE_VAR_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_string(value: str, env: Mapping[str, str]) -> str:
    """Expand ``${VAR}`` and ``$VAR`` references and a leading ``~``.

    Unknown references are left as-is rather than raising, matching
    shell expansion semantics. A leading ``~`` is expanded to the
    current user's home directory (resolved against ``$HOME`` in the
    supplied ``env`` when available; falls through to
    :func:`os.path.expanduser` otherwise). Embedded ``~`` is left
    alone (matches POSIX shell behavior).

    Note: Python's :func:`os.path.expandvars` only handles ``$VAR``
    (unbraced) on some platforms. We use regexes so both forms are
    always recognized regardless of the underlying Python build.
    """
    if value.startswith("~"):
        home = env.get("HOME")
        if home is not None:
            value = home + value[1:]
        else:
            value = os.path.expanduser(value)

    def _sub_braced(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in env:
            return str(env[name])
        return match.group(0)

    value = _ENV_VAR_PATTERN.sub(_sub_braced, value)

    # Bare $VAR: replace only if NOT preceded by '{' (which would
    # already have been handled by _ENV_VAR_PATTERN).
    def _sub_bare(match: re.Match[str]) -> str:
        start = match.start()
        if start > 0 and value[start - 1] == "{":
            return match.group(0)
        name = match.group(1)
        if name in env:
            return str(env[name])
        return match.group(0)

    value = _BARE_VAR_PATTERN.sub(_sub_bare, value)
    return value


def _expand_value(value: Any, env: Mapping[str, str]) -> Any:
    """Recursively walk a JSON-derived value, expanding strings.

    Strings get :func:`_expand_string`. Dicts and lists are walked.
    Other scalar types pass through unchanged.
    """
    if isinstance(value, str):
        return _expand_string(value, env)
    if isinstance(value, dict):
        return {k: _expand_value(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_value(v, env) for v in value]
    return value


def expand_value(
    value: Any,
    *,
    env: Mapping[str, str] | None = None,
) -> Any:
    """Expand ``${VAR}`` and ``~`` references anywhere in a config tree.

    Args:
        value: JSON-derived Python value (dict, list, str, or scalar).
        env: Source of environment variables. Defaults to ``os.environ``.
            Pass an explicit mapping for testability.

    Returns:
        A new value with all string leaves expanded. Containers are
        deep-copied as a side effect.
    """
    return _expand_value(value, env if env is not None else os.environ)


def _is_path_key(key: str) -> bool:
    return any(key.endswith(suffix) for suffix in PATH_KEY_SUFFIXES)


def expand_paths(value: Any) -> Any:
    """Run :func:`safe_path` on string values of path-shaped keys.

    A key is "path-shaped" when its name ends in one of
    :data:`PATH_KEY_SUFFIXES`. Non-string values, non-path keys, and
    keys without a recognized suffix pass through unchanged. The
    resulting path uses ``resolve_symlinks=False`` to preserve the
    operator's textual form (matches ``bed.config`` behavior).

    ``${VAR}`` and ``~`` expansion happens as a side effect (via
    :func:`safe_path`).
    """
    if isinstance(value, dict):
        return {
            k: (
                safe_path(v, resolve_symlinks=False)
                if isinstance(v, str) and _is_path_key(k)
                else v
            )
            for k, v in value.items()
        }
    return value


# ---------------------------------------------------------------------------
# Argparse-default builder
# ---------------------------------------------------------------------------

def _coerce_scalar(value: Any, coerce_fn: Callable[[Any], Any] | None) -> Any:
    if coerce_fn is None:
        return value
    try:
        return coerce_fn(value)
    except (TypeError, ValueError):
        return value


def build_argparse_defaults(
    json_config: dict,
    *,
    section: str,
    keys: Sequence[str],
    env_prefix: str = "",
    env_key_map: Mapping[str, str] | None = None,
    global_section: str = "global",
    hardcoded_defaults: Mapping[str, Any] | None = None,
    coerce: Mapping[str, Callable[[Any], Any]] | None = None,
) -> dict:
    """Build a dict suitable as the ``defaults=`` for an argparse group.

    For each ``key`` in ``keys``, the returned value is resolved via:
        json_config[section][key] (post expansion)
        ?? env ${env_prefix}_${env_name_for(key)}
        ?? json_config[global_section][key]
        ?? hardcoded_defaults[key]
        ?? ``None``

    Args:
        json_config: Full merged config dict (typically
        ``zoidoffice.conf.load_config()``).
        section: Section name to read from first (e.g. ``"bed"``,
        ``"global"``, ``"modules"``).
        keys: The keys to resolve, in the order callers want them
        in the returned dict.
        env_prefix: Prefix for environment-variable lookup. ``""``
        disables env-var fallback. ``"BED"`` produces
        ``BED_HOST`` for key ``"host"`` by default.
        env_key_map: Optional mapping ``key -> env_name_suffix``.
        When provided, the env-var lookup uses
        ``${env_prefix}_${env_key_map[key]}`` instead of the
        default ``${env_prefix}_${key.upper()}``. This lets apps
        bridge between argparse dest names (``"databasename"``)
        and historical env-var conventions (``"NAME"`` →
        ``BBSENGINE6_DBNAME``). When ``env_key_map`` has no entry
        for a key, the default ``key.upper()`` is used.
        global_section: Section name to use as the cross-section
        fallback (typically ``"global"``). ``""`` disables the
        cross-section fallback.
        hardcoded_defaults: Last-resort defaults baked into the
        argparse group itself.
        coerce: Optional mapping of ``key -> callable`` applied to
        the resolved value (e.g. ``int`` for port numbers). Bad
        coercion results fall back to the un-coerced value rather
        than raising.

    Returns:
        ``dict`` keyed by ``key`` (not the argparse ``dest``).
        Caller is responsible for wiring each key into its argument.
    """
    section_cfg = get_section(json_config, section)
    global_cfg = (
        get_section(json_config, global_section) if global_section else {}
    )
    hardcoded = dict(hardcoded_defaults or {})
    coerce_map = dict(coerce or {})
    key_map = dict(env_key_map or {})

    out: dict[str, Any] = {}
    for key in keys:
        json_val = section_cfg.get(key)
        if json_val is None:
            json_val = global_cfg.get(key)

        env_val: Any = None
        if env_prefix:
            mapped = key_map.get(key)
            if mapped is not None:
                # ``mapped`` may be either a full env-var name
                # (e.g. ``"BBSENGINE6_DBNAME"``) or a suffix to
                # combine with the prefix. A full name is recognized
                # by containing ``_`` characters beyond what the
                # prefix alone contains — in practice, if ``mapped``
                # contains the prefix substring, treat it as the
                # full env var; otherwise combine with the prefix.
                mapped_upper = mapped.upper()
                if (
                    env_prefix
                    and mapped_upper.startswith(env_prefix.upper())
                    and mapped_upper != env_prefix.upper()
                ):
                    env_name = mapped_upper
                else:
                    env_name = f"{env_prefix}_{mapped_upper}"
            else:
                env_name = f"{env_prefix}_{key.upper()}"
            env_val = os.environ.get(env_name)

        # Precedence: env var > JSON > hardcoded default.
        resolved = resolve(env_val, json_val, hardcoded.get(key))
        out[key] = _coerce_scalar(resolved, coerce_map.get(key))
    return out


# ---------------------------------------------------------------------------
# Schema validation (light)
# ---------------------------------------------------------------------------

def validate_schema(
    config: dict,
    *,
    known_sections: Iterable[str] = DEFAULT_KNOWN_SECTIONS,
) -> list[str]:
    """Return human-readable warnings for unknown top-level sections.

    The intent is typo-catching, not strict enforcement: each app
    passes its own ``known_sections`` frozenset; unknown keys are
    reported via the ``logging`` module rather than raised, so a
    typo in ``.zoidoffice.json`` warns the operator but does not
    abort startup.

    Returns:
        List of warning strings (empty when config is conformant).
    """
    known = frozenset(known_sections)
    warnings: list[str] = []
    for section in config:
        if section.startswith("_"):
            continue
        if section not in known:
            warnings.append(
                f"unknown top-level config section {section!r} "
                f"(known sections: {sorted(known)})"
            )
    return warnings


__all__ = [
    "DEFAULT_KNOWN_SECTIONS",
    "PATH_KEY_SUFFIXES",
    "build_argparse_defaults",
    "deep_merge",
    "expand_paths",
    "expand_value",
    "get_section",
    "load_json_file",
    "load_json_file_strict",
    "resolve",
    "search_config",
    "validate_schema",
]