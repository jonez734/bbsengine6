# bbsengine6.io.inputchoice Specification

## Overview

`inputchoice.py` provides single-character choice input from the terminal. It displays a prompt with available options and waits for a single keypress.

## Dependencies

- `echo.py`: Terminal output
- `getch.py`: Key input (getch_str)

## Public API

### Main Function

```python
def inputchoice(prompt:str, options:str, default:str="", **kwargs) -> str | None
```

Prompts user for a single character choice.

**Parameters:**
- `prompt`: Prompt text to display
- `options`: Valid option characters (e.g., "YN", "abc")
- `default`: Default choice if Enter is pressed (default: "")
- `noneok`: If True, allow empty input to return None (default: False)
- `help`: Help text (str) or callable, shown on `KEY_F1` or `KEY_HELP` (default: None)
- `f2_handler`: Text or callable run on `KEY_F2`, then the prompt is redrawn
- `rewriteprompt`: If True, rewrite prompt with colored options (default: False)
- `args`: Application args namespace (for database operations in kwargs handlers)
- `pool`: Database connection pool (alternative to args for direct pool access)
- `**kwargs`: Additional arguments passed to getch and notification handlers

**Returns:**
- Selected character (uppercase), when it is one of `options`
- A function-key name (for example `"KEY_F5"`), when one is pressed. The loop stops on
  any `KEY_` name except Enter, F1, HELP and F2, so the caller receives it
- Default value if Enter pressed and default is set
- `None` if Enter pressed and `noneok=True`

**Behavior:**
- Options are converted to uppercase for matching
- Keys that are not in `options` beep and are ignored
- `KEY_F1` and `KEY_HELP` show `help` (text or callable), then the prompt is redrawn
- `?` is an ordinary character. It is not a help key unless `?` is in `options`
- Pass `args` and/or `pool` in kwargs to enable notification checking during input

## Examples

```python
result = inputchoice("Continue?", "YN")                     # "Y" or "N"
result = inputchoice("Select:", "abc", default="a")         # "A", "B", or "C"
result = inputchoice("Choice?", "YN", noneok=True)          # "Y", "N", or None
result = inputchoice("Select:", "ABC", args=args, pool=pool)  # with notifications
```

## Key Handling

| Key | Action |
|-----|--------|
| Enter | Return the default; `None` if `noneok=True`; otherwise bell and wait |
| F1 / HELP | Show `help`, redraw prompt |
| F2 | Run `f2_handler`, redraw prompt |
| other `KEY_*` | Returned to the caller (not ignored) |
| `?` | Ordinary character; bell unless `?` is in `options` |
| Valid option | Return option |
| Other | Bell (invalid) |
