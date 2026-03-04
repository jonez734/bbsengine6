# DEPRECATED: This module is not used.
# asimov.io.echovars Specification

## Overview

`echovars.py` provides a global variable storage system for echo command values. It allows storing and retrieving named variables that can be used in echo formatting.

## API

### Variables Dictionary

```python
variables = {}
```

Global dictionary storing all echo variables.

### Functions

```python
def set(name: str, value) -> None:
    """Set a variable by name."""
```

```python
def get(name: str, default=None) -> str:
    """Get a variable by name. Returns default if not found."""
```

```python
def clear() -> None:
    """Clear all variables."""
```

```python
def save() -> bool:
    """Save current variables to stack. Returns True on success."""
```

```python
def restore() -> None:
    """Restore variables from stack."""
```

## Example Variables

- `boxcolor`: Box color for UI elements
- `titlecolor`: Title text color
- `promptcolor`: Prompt text color
- `inputcolor`: Input text color
- `level.debug`: Debug log prefix color
- `level.warning`: Warning log prefix color
- `level.error`: Error log prefix color
