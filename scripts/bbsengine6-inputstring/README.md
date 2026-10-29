# bbsengine6 input tests

Checks for `inputstring()`, `inputinteger()` and tab completion. Each check
types keystrokes into a pseudo-terminal and compares the result.

## What you need

| Needed | Notes |
|---|---|
| Linux (or another POSIX system) | Uses ptys and termios. |
| Python 3.10 or newer | Standard library only for the default mode. |
| `bbsengine6` | Either installed in the active environment, or a source tree passed with `--src`. |
| `pytest` | Only for `--pytest`. |

Not needed: a display, gnome-terminal, ssh, or PostgreSQL.

## Run it

```sh
# Test the installed bbsengine6
python3 run_inputstring_tests.py

# Test a source checkout (PATH contains the bbsengine6 package directory)
python3 run_inputstring_tests.py --src /path/to/bbsengine6/py/src

# One group: tab | noneok | allowed | filter | paste
python3 run_inputstring_tests.py --src PATH --only tab

# Run through pytest instead
python3 run_inputstring_tests.py --pytest --src PATH

# Slow machine: wait longer between keystrokes (default 0.25 s)
python3 run_inputstring_tests.py --delay 0.5

# Manual check in the current terminal (Tab, Enter, paste, Ctrl-C to quit)
python3 run_inputstring_tests.py --interactive
```

The script prints which copy of `bbsengine6` it tested. Check that line first:
if it is not the copy you meant, pass `--src`.

## Reading the result

- Each line is `PASS` or `FAIL` with its group.
- A `FAIL` shows `expected` and `got`.
- Exit status: `0` all passed, `1` a check failed, `2` bbsengine6 could not be
  imported or `--src` is wrong.

## What is covered

- **tab**: completion of the first and second word, ambiguous and unmatched
  prefixes, double Tab on empty input.
- **noneok**: empty Enter accepted by default; rejected with `noneok=False`.
- **allowed**: disallowed characters dropped while typing and in a paste.
- **filter**: regex checked on Enter; `inputinteger` behavior.
- **paste**: plain, tab, control byte, UTF-8, and long pastes.

## Known limits

- Timing-based: the script writes keys with a delay. On a loaded machine a
  check can fail for timing reasons; rerun, or raise `--delay`.
- Covers `inputstring` and `inputinteger`, not the mouse-state behavior or the
  editor. Those need a real terminal to check.
