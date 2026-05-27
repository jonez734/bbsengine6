# bbsengine6.io.inputinteger Specification

## Overview

`inputinteger.py` provides integer input by wrapping `inputstring` with a regex filter to validate numeric input.

## Dependencies

- `inputstring.py`: Core string input

## Public API

### Main Function

```python
def inputinteger(
    prompt: str,
    oldvalue: int | str | None = None,
    **kwargs
) -> int | list[int] | None
```

Prompts user for integer input with optional validation.

**Parameters:**
- `prompt`: Prompt text to display
- `oldvalue`: Pre-fill value (converted to string, default: None)
- `**kwargs`: Passed to `inputstring`

**Returns:**
- `int` for single integer input
- `list[int]` for multiple integers (space/comma separated)
- `None` if input is empty, cancelled, or invalid

**Default Filter:**
- Matches integers with optional sign (+/-)
- Allows comma or space separated values
- Does not match empty strings

## Examples

```python
result = inputinteger("Enter age:")  # Returns int
result = inputinteger("Enter numbers:")  # Returns list[int] with space/comma separator
result = inputinteger("Enter value:", oldvalue=42)  # Pre-fills with 42
```