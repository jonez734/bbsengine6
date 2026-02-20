# asimov.io.inputinteger Specification

## Overview

`inputinteger.py` provides integer input by wrapping `inputstring` with a regex filter to validate numeric input.

## Dependencies

- `inputstring.py`: Core string input

## Public API

### Main Function

```python
def inputinteger(prompt, oldvalue=None, **kwargs) -> int | list[int] | None
```

Prompts user for integer input with optional validation.

**Parameters:**
- `prompt`: Prompt text to display
- `oldvalue`: Pre-fill value (default: None)
- `filter`: Regex pattern to filter input (default: `r"^([+-]?[1-9]\d*|0)[ ,]?$"`)
- `**kwargs`: Passed to `inputstring`

**Returns:**
- `int` for single integer input
- `list[int]` for multiple integers (space/comma separated)
- `None` if input is empty or invalid

**Default Filter:**
- Matches integers with optional sign (+/-)
- Allows comma or space separated values
- Does not match empty strings

## Examples

```python
result = inputinteger("Enter age:")  # Returns int
result = inputinteger("Enter numbers:", filter=r"^\d+\s+\d+$")  # Returns list[int]
result = inputinteger("Enter value:", oldvalue=42)  # Pre-fills with 42
```
