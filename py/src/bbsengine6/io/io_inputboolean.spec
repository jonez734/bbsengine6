# asimov.io.inputboolean Specification

## Overview

`inputboolean.py` provides a simple yes/no boolean input by wrapping `inputchoice`. It prompts the user with options (default Y/N) and returns a boolean value.

## Dependencies

- `inputchoice.py`: Core choice selection
- `echo.py`: Terminal output

## Public API

### Main Function

```python
def inputboolean(prompt:str, default:str=None, options="YN", **kwargs) -> bool | None
```

Prompts user for a boolean response.

**Parameters:**
- `prompt`: Prompt text to display
- `default`: Default value (default: None)
- `options`: Options string (default: "YN")
- `**kwargs`: Passed to `inputchoice`

**Returns:**
- `True` for "Y" or "T" (case-insensitive)
- `False` for "N" or "F" (case-insensitive)
- `None` if input fails or is cancelled

**Behavior:**
- Displays "Yes" or "No" echo after selection
- Falls back to `inputchoice` for the actual key handling

## Examples

```python
result = inputboolean("Continue?")  # Returns True/False
result = inputboolean("Enable?", options="TF")  # Returns True/False
```
