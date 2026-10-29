# bbsengine6.io.inputinteger Specification

## Overview

`inputinteger.py` reads an integer. It is `inputstring()` with two settings: an
`allowed` set that limits what can be typed, and a `filter` regex that checks the
whole value on Enter.

## Dependencies

- `inputstring.py`: the line editor that does the reading

## Public API

```python
def inputinteger(
    prompt: str,
    oldvalue: int | str | None = None,
    **kwargs
) -> int | None
```

**Parameters:**
- `prompt`: Prompt text to display
- `oldvalue`: Pre-fill value, converted to a string (default: `None`, empty)
- `**kwargs`: Passed to `inputstring`. `filter` and `allowed` may be given to
  override the defaults below.

**Defaults set by `inputinteger`:**
- `allowed="0123456789+- ,"`: only digits, sign, space and comma can be typed. Other
  characters beep and are dropped (see `io_inputstring.md`, Paste Input and Typing).
- `filter=r"^([+-]?[1-9]\d*|0)[ ,]?$"`: checked on Enter. The value must be one
  integer with an optional sign and at most one trailing separator.

**Accepted and rejected values (default filter):**

| Entry | Result |
|---|---|
| `42`, `-7`, `+3`, `0` | accepted |
| `12 ` (trailing space), `1,` | accepted (one trailing separator) |
| `007` | rejected: leading zero |
| `1 2`, `1,2` | rejected: more than one value |
| `abc` | cannot be typed (not in `allowed`) |
| empty | `inputstring` returns `""` (its default is `noneok=True`), which becomes `None` |

A rejected value beeps and reprompts, as `inputstring` does for any failed `filter`.

**Returns:**
- `int` for an accepted value
- `None` if the result is empty, or if `int()` fails on the text (only the default filter stops most of these)

## Lists

`inputinteger` returns one `int` or `None`. A caller that wants several integers must
pass its own `filter`, read the string, and split it. No list-entry filter is built in.

## Examples

```python
n = inputinteger("Enter age: ")                       # int
n = inputinteger("Enter value: ", oldvalue=42)        # pre-filled with 42
n = inputinteger("Enter level: ", filter=r"^[1-9]$")  # single digit 1-9 only
```

## Fixed

The return annotation promised `list[int]`, and a list branch was unreachable because
`inputstring` returns a string. Both are removed: the return type is `int | None`.
