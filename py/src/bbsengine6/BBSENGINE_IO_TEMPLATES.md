# BBSENGINE6 TUI Template System

## Overview

The TUI (Terminal User Interface) template system for bbsengine6 allows separating UI layout from code, similar to how Smarty templates work for the web interface.

## Directory Structure

```
bbsengine6/py/src/bbsengine6/
├── tpl/                          # Built-in templates
│   ├── menu.tpl
│   ├── form.tpl
│   ├── confirm.tpl
│   ├── list.tpl
│   └── header.tpl
```

## Template Loading Priority

1. Check site-specific `config.template_dir` first
2. Fall back to built-in `bbsengine6/tpl/` directory

This matches the Smarty template loading pattern used in www.

## Variable Syntax

- **Template variables**: `{varname}` - replaced at render time with values passed to the template function
- **Runtime variables**: `{var:varname}` - existing io.echo() behavior, uses predefined runtime variables

Example template (`menu.tpl`):
```
{var:titlecolor}=== {title} ==={var:normalcolor}
{var:optioncolor}[1] {item1}{var:normalcolor}
{var:optioncolor}[2] {item2}{var:normalcolor}
{var:optioncolor}[X] eXit{var:normalcolor}
```

## API

```python
from bbsengine6 import io

# Option 1: Load template, substitute variables, return string
template = io.load_template("menu.tpl", title="Main Menu", item1="Files", item2="Mail")
io.echo(template)

# Option 2: Load, substitute, and echo in one call
io.echo_template("menu.tpl", title="Main Menu", item1="Files", item2="Mail")
```

### Keyword Args for echo_template()

- `page_size`: If > 0, pause every N lines with "More?" prompt (default: 0, no paging)
- `raw`: If True, output raw text without interpreting {var:xxx} commands (default: False)
- `wordwrap`: Enable/disable word wrapping (default: True)

```python
io.echo_template("menu.tpl", page_size=20)  # with paging
io.echo_template("menu.tpl", raw=True)       # raw output
```

## Implementation Details

### Functions in io/echo.py

- `_get_template_dirs()` - internal: get list of template search paths
- `_load_template(name)` - internal: load template file with fallback logic
- `load_template(name, **vars)` - load + substitute `{varname}` placeholders
- `echo_template(name, **vars)` - load, substitute, and echo in one call

### Template Files

- Use `.tpl` extension
- Store in `py/src/bbsengine6/tpl/` for built-in templates
- Site-specific templates go in `config.template_dir` (override built-ins)

### echo_template() Implementation

`echo_template()` is a thin wrapper around `echo_file()`:
- Loads template + substitutes variables
- Writes to temp file
- Calls `echo_file()` which provides paging (`page_size`), `raw`, and `wordwrap` options

## Future Ideas (Not Implemented)

These are potential features to consider in the future:

### 1. Template Directory as List
```python
io.setvar("template_dir", ["/my/site/tpl", "/shared/tpl", "bbsengine6/tpl"])
# Searches in order, first match wins (like os.path in Python)
```

### 2. Template Includes
```python
# In template:
{include:header.tpl}
# Would include header.tpl content at that location
```

### 3. Variable Modifiers
```python
# In template:
{title|upper}  -> "MAIN MENU"
{name|lower}  -> "alice"
```

### 4. Template Caching
- Compile templates to cache for performance
- Smarty-style compiled template directory