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
) -> int | list[int] | None
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
- `None` if the result is empty, or if `int()` fails on the text

## Lists are not accepted by the default filter

The return type includes `list[int]`, and the code has a branch for a list result.
`inputstring` returns a string, not a list, so that branch is never taken, and the
default filter rejects `1 2`. A caller that wants several integers must pass its own
`filter` and split the string itself. No list-entry filter is built in.

## Examples

```python
n = inputinteger("Enter age: ")                       # int
n = inputinteger("Enter value: ", oldvalue=42)        # pre-filled with 42
n = inputinteger("Enter level: ", filter=r"^[1-9]$")  # single digit 1-9 only
```

## Known gap

The return annotation `int | list[int] | None` promises a list the module never
returns. The annotation should be `int | None`. Correcting the annotation is a code
change, recorded here and not made in this pass.
