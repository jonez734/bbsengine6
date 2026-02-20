# asimov.io.inputchoice Specification

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
- `help`: Help text or callback (default: None)
- `rewriteprompt`: If True, rewrite prompt with colored options (default: False)
- `**kwargs`: Additional arguments

**Returns:**
- Selected character (uppercase)
- Default value if Enter pressed and default is set
- `None` if Enter pressed and `noneok=True`
- `?` or `KEY_HELP` triggers help display

**Behavior:**
- Options are converted to uppercase for matching
- Invalid keys trigger bell
- Help key (?) displays help text/callback then redraws prompt

## Examples

```python
result = inputchoice("Continue?", "YN")  # Returns "Y" or "N"
result = inputchoice("Select:", "abc", default="a")  # Returns "A", "B", or "C"
result = inputchoice("Choice?", "YN", noneok=True)  # Returns "Y", "N", or None
```

## Key Handling

| Key | Action |
|-----|--------|
| Enter | Return default or None (if noneok) or bell |
| ? / F1 | Show help |
| KEY_* | Ignore (function keys) |
| Valid option | Return option |
| Other | Bell (invalid) |
