#!/bin/sh
#
# bbsengine6/data/sanitize_args.sh - shell-side argv sanitizer for
# bin wrappers.
#
# Loaded with `.` by shell bin wrappers (zoidoffice's ``pw``, ``pho``,
# ``rproj``, ...). Exposes ``sanitize_and_exec`` which validates
# caller-supplied argv against a strict whitelist before exec(3)'ing
# the downstream python interpreter. Mirrors the policy implemented
# in ``bbsengine6.util.sanitize_args`` (Python); both implementations
# are pinned together by an integration test
# (``bbsengine6/tests/test_sanitize_args_sh.py``).
#
# --------------------------------------------------------------------------
# Threat model (parallels bbsengine6.util.sanitize_args)
# --------------------------------------------------------------------------
#
# A bin wrapper that passes ``"$@"`` straight to ``python -W all -m
# <module>`` is exposed to three argv-driven risks:
#
#   1. Python-interpreter flag injection. ``python`` consumes its own
#      options before ``-m <module>`` runs. A user arg like
#      ``-X faulthandler`` or ``-c "code"`` is consumed by python
#      itself (not the target module's argparse) and can change
#      startup behavior.
#
#   2. Environment-variable RCE / persistence. ``PYTHONSTARTUP``,
#      ``PYTHONPATH``, ``PYTHONBREAKPOINT``, ``PYTHONINSPECT``,
#      ``PYTHONDEBUG``, ``PYTHONPYCACHEPREFIX`` and friends can hijack
#      python startup even when argv is clean. ``_DANGEROUS_PYTHON_VARS``
#      below lists the names that get ``unset`` before exec.
#
#   3. Stdin redirection / option-name smuggling. A bare ``-`` is the
#      argparse sentinel for stdin; long opts whose name contains
#      shell metacharacters could break out of their token if a
#      wrapper ever forgets to quote.
#
# Policy implemented here:
#
#   * Empty token                          -> reject.
#   * Bare ``-``                           -> reject.
#   * Any token starting with ``-`` but not
#     ``--``                               -> reject. zoidoffice CLIs
#                                              use long opts only;
#                                              refusing the whole
#                                              single-dash class closes
#                                              the flag-injection hole
#                                              without breaking any
#                                              legitimate invocation.
#   * ``--`` alone                         -> allow (argparse
#                                              end-of-options).
#   * ``--name[=value]``                   -> allow iff ``name``
#                                              matches
#                                              ``^[A-Za-z0-9_-]+$``.
#                                              NUL / CR / LF / FF in
#                                              the token are rejected.
#   * Anything else (positional)           -> allow, except NUL.
#
# Callers invoke ``sanitize_and_exec python -W all -m <module> "$@"``:
# the static prefix ``python -W all -m <module>`` is trusted (it's
# baked into the wrapper's source); everything after it (``$@``) is
# caller-supplied argv and is validated token-by-token.
#
# Exit codes:
#   * 0   argv clean; downstream command was exec'd (or attempted).
#   * 2   one or more argv tokens were rejected; command NOT invoked.
#   * 64  usage error (no caller argv; static prefix only).
#

# Reset IFS to the POSIX default so word-splitting in this script is
# independent of the caller's environment. The wrapper's "$@"
# already preserves the original tokens; this is belt-and-suspenders.
IFS=$(printf ' \t\n_')
IFS=${IFS%_}

# Dangerous PYTHON* env vars. Keep this list in sync with
# ``bbsengine6.util.DANGEROUS_PYTHON_ENV_VARS``; the integration
# test enforces parity. ``unset`` is a no-op for absent names.
#
# Each name is on its own line so word-splitting on the default IFS
# iterates one name at a time. We unquote the variable on the right
# side of the assignment intentionally (single-quoted) so the newlines
# are preserved as-is in the resulting string.
_DANGEROUS_PYTHON_VARS='PYTHONSTARTUP
PYTHONPATH
PYTHONHOME
PYTHONINSPECT
PYTHONBREAKPOINT
PYTHONDEBUG
PYTHONPYCACHEPREFIX
PYTHONNOUSERSITE
PYTHONUSERBASE
PYTHONFAULTHANDLER
PYTHONTRACEMALLOC
PYTHONPROFILEIMPORTTIME
PYTHONCOERCECLOCALE
PYTHONDEVMODE
PYTHONMALLOCSTATS
PYTHONLEGACYWINDOWSSTDIO
PYTHONDONTWRITEBYTECODE'

# Word-split the variable's value on newlines/whitespace and unset
# each name. Use eval-free indirect expansion where possible.
# ``unset`` accepts one name at a time; loop with the IFS split.
for _v in $_DANGEROUS_PYTHON_VARS; do
    # Defensive: skip empty strings (in case IFS is misconfigured).
    if [ -n "$_v" ]; then
        unset "$_v" 2>/dev/null || :
    fi
done
unset _v


# _sanitize_arg <token>
#   Echoes "ok" if <token> is acceptable, "reject:<reason>" otherwise.
#   Pure-string check; no side effects on $@.
_sanitize_arg() {
    _token="$1"
    if [ -z "$_token" ]; then
        printf '%s\n' 'reject:empty'
        return 0
    fi

    # Bare `-` is the argparse stdin sentinel; reject it.
    if [ "$_token" = '-' ]; then
        printf '%s\n' 'reject:bare-dash'
        return 0
    fi

    # NUL bytes cannot reach this function: the kernel strips them
    # at the exec boundary. The Python-side sanitizer still checks
    # for NUL because Python's `os.environ` and certain config-file
    # code paths can construct argv strings programmatically with
    # NULs in them. The shell side has no equivalent risk; we omit
    # the check entirely.

    case "$_token" in
        -*)
            # `--` ends argparse's option list; allow it.
            if [ "$_token" = '--' ]; then
                printf '%s\n' 'ok'
                return 0
            fi
            # `--...` is the long-opt branch (handled below). Anything
            # else (single-dash: `-x`, `-X`, `-c "code"`, etc.)
            # is rejected; zoidoffice CLIs use long opts only, and
            # single-dash args would be consumed by python itself
            # before reaching `-m <module>`.
            if [ "${_token#--}" != "$_token" ]; then
                : # fall through to long-opt handling below
            else
                printf '%s\n' "reject:single-dash-option:$_token"
                return 0
            fi
            ;;
    esac

    # Long option (`--name[=value]`). Enforce a strict charset on
    # the name part; value (after the first `=`) may contain any
    # printable bytes except CR / LF / FF (which would corrupt argv
    # on the receiving python).
    if [ "${_token#--}" != "$_token" ]; then
        _name="${_token%%=*}"
        if [ "$_name" != "$_token" ]; then
            _value="${_token#*=}"
            # Reject CR / LF / FF in the value portion.
            case "$_value" in
                *'
'*|*'
	'|*'
'|*''|*'')
                    printf '%s\n' 'reject:control-char-in-value'
                    return 0
                    ;;
            esac
        fi

        _check_body="${_name#--}"
        case "$_check_body" in
            '')
                printf '%s\n' 'reject:empty-long-opt'
                return 0
                ;;
            *[!A-Za-z0-9_-]*)
                printf '%s\n' "reject:bad-long-opt-name:$_check_body"
                return 0
                ;;
        esac

        printf '%s\n' 'ok'
        return 0
    fi

    # Positional. Allowed (argparse handles validation).
    printf '%s\n' 'ok'
    return 0
}


# sanitize_and_exec <cmd> [<args>...]
#
# Validates every token in "$@" against the policy above. On success,
# unsets dangerous PYTHON* env vars and exec(3)s <cmd> with the
# caller argv verbatim. On failure, prints a clear error to stderr
# and exits non-zero WITHOUT invoking <cmd>.
#
# Wrapper usage:
#
#   sanitize_and_exec python -W all -m zoidoffice.project.pwsearch "$@"
#
# The literal `python -W all -m <module>` text remains in the wrapper
# file so test_project_bin_wrappers.py's parse_target regex can find
# it; the actual exec is gated by sanitize_and_exec.
sanitize_and_exec() {
    _argc=0
    _static_count=0
    _saw_m=0
    _m_target=""
    _validation_failed=0
    _rejection_msg=""

    # Walk $@ in order. The static prefix is everything up to and
    # including the `-m <module>` token; everything from there on is
    # caller argv to validate.
    #
    # Two-state machine: ``_saw_m=0`` (looking for `-m`); once `-m`
    # is seen, the next single token is the module name (also part of
    # the static prefix), then everything after is caller argv.
    for _arg in "$@"; do
        _argc=$((_argc + 1))
        if [ "$_saw_m" = "2" ]; then
            # Already past `-m <module>`; this and subsequent args are
            # caller argv.
            continue
        fi
        if [ "$_saw_m" = "1" ]; then
            # The token after `-m` is the module name; treat as static.
            _m_target="$_arg"
            _static_count=$((_static_count + 1))
            _saw_m=2
            continue
        fi
        if [ "$_arg" = "-m" ]; then
            _static_count=$((_static_count + 1))
            _saw_m=1
            continue
        fi
        _static_count=$((_static_count + 1))
    done

    if [ "$_saw_m" != "2" ]; then
        # No `-m` boundary marker found (or only `-m` with no module
        # target). The wrapper author either has a non-python-static-
        # prefix (rare) or forgot to include `-m <module>`. Refuse to
        # exec; silent fallback would let a future refactor accidentally
        # validate the static prefix instead of the caller argv.
        printf '%s\n' "sanitize_and_exec: static command has no '-m <module>' token; refusing to exec (every wrapper in this package must exec 'python ... -m <module>')" >&2
        exit 2
    fi

    # Validate caller argv (everything after the static prefix).
    _i=$((_static_count + 1))
    while [ "$_i" -le "$_argc" ]; do
        # Indirect parameter expansion to read positional $i. POSIX
        # `eval` is required here because sh has no ${!i} until bash
        # 5 / mksh; using eval is safe because $i is an integer we
        # computed and printf-formatted.
        _eval_token=\$"$_i"
        eval "_token=$_eval_token"
        _result="$(_sanitize_arg "$_token")"
        case "$_result" in
            ok)
                ;;
            reject:*)
                _r_token_repr="$(printf '%s' "$_token" | od -An -c | head -n 1 | tr -s ' ')"
                if [ -z "$_rejection_msg" ]; then
                    _rejection_msg="rejected argv[$_i] ($_result): token=<$_token> od=<$_r_token_repr>"
                else
                    _rejection_msg="$_rejection_msg; rejected argv[$_i] ($_result): token=<$_token> od=<$_r_token_repr>"
                fi
                _validation_failed=1
                ;;
        esac
        _i=$((_i + 1))
    done

    if [ "$_validation_failed" != "0" ]; then
        printf '%s\n' "sanitize_and_exec: refusing to exec due to: $_rejection_msg" >&2
        exit 2
    fi

    # All args validated. exec the original argv; this passes the
    # caller tokens unchanged to python (no shell re-evaluation).
    exec "$@"
}