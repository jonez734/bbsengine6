#!/bin/sh
# capture-session.sh -- record a terminal session with script(1) for bug reports.
#
# Captures the exact bytes a program writes to the terminal, plus a timing file
# so the session can be replayed with scriptreplay(1).
#
# Usage:
#   capture-session.sh [-o OUTDIR] [-n NAME] [-c COMMAND] [-e] [-h]
#
#   -o OUTDIR   directory for the capture (default: ./captures)
#   -n NAME     base name for the files (default: session-YYYYmmdd-HHMMSS)
#   -c COMMAND  command to run inside the session (default: $SHELL)
#   -e          also record typed input (script -E always; default never)
#   -h          show this help
#
# Output (in OUTDIR):
#   NAME.typescript   raw script(1) file, with its banner and footer (replay this)
#   NAME.clean        the same bytes without the banner and footer (read this)
#   NAME.timing       timing data for: scriptreplay NAME.timing NAME.typescript
#   NAME.info         the terminal size and command used
#
# Example, capturing one inputstring prompt:
#   capture-session.sh -n arrows -c "python3 /tmp/prompt.py"
#   # in the session: type, press left twice, then exit the program
#
# Requires: script (util-linux). Exit status: 0 ok, 1 usage, 2 script missing.

set -eu

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-1}"
}

OUTDIR="./captures"
NAME=""
CMD="${SHELL:-/bin/sh}"
ECHO_MODE="never"   # script -E: never | always | auto

while getopts "o:n:c:eh" opt; do
    case "$opt" in
        o) OUTDIR="$OPTARG" ;;
        n) NAME="$OPTARG" ;;
        c) CMD="$OPTARG" ;;
        e) ECHO_MODE="always" ;;
        h) usage 0 ;;
        *) usage 1 ;;
    esac
done

if ! command -v script >/dev/null 2>&1; then
    echo "capture-session.sh: 'script' is not installed." >&2
    echo "Install util-linux (Fedora: dnf install util-linux)." >&2
    exit 2
fi

if [ -z "$NAME" ]; then
    NAME="session-$(date +%Y%m%d-%H%M%S)"
fi

mkdir -p "$OUTDIR"
TYPESCRIPT="$OUTDIR/$NAME.typescript"
CLEAN="$OUTDIR/$NAME.clean"
TIMING="$OUTDIR/$NAME.timing"
INFO="$OUTDIR/$NAME.info"

if [ -e "$TYPESCRIPT" ]; then
    echo "capture-session.sh: $TYPESCRIPT already exists; choose another -n." >&2
    exit 1
fi

COLS="$(tput cols 2>/dev/null || echo unknown)"
ROWS="$(tput lines 2>/dev/null || echo unknown)"
{
    echo "date:     $(date -Iseconds)"
    echo "terminal: ${TERM:-unknown} (${COLS}x${ROWS})"
    echo "command:  $CMD"
    echo "script:   $(script --version 2>/dev/null | head -1)"
} > "$INFO"

echo "Recording to $TYPESCRIPT"
echo "Type 'exit' (or end the command) to stop."

# util-linux script(1) options used:
#   -q       quiet: no start/done banners in the capture
#   -f       flush after every write, so a crash keeps the bytes written so far
#   -T FILE  timing file, for scriptreplay(1)
#   -E WHEN  echo of typed input: "never" keeps keystrokes out of the capture
#   -c CMD   command to run inside the session
set +e
script -q -f -T "$TIMING" -E "$ECHO_MODE" -c "$CMD" "$TYPESCRIPT"
STATUS=$?
set -e

# script(1) writes its own banner and footer into the file. Keep the raw file: the
# timing file counts its bytes, so removing the header would break scriptreplay.
# Write a cleaned copy (program bytes only) next to it for reading.
if [ -f "$TYPESCRIPT" ]; then
    awk 'NR==1 && /^Script started on /{next} /^Script done on /{next} {print}' \
        "$TYPESCRIPT" > "$CLEAN"
fi

echo "Saved: $TYPESCRIPT (raw) and $CLEAN (program output only)"
echo "Replay: scriptreplay $TIMING $TYPESCRIPT"
echo "Info:   $INFO"
exit "$STATUS"
