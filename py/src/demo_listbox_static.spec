# demo_listbox_static Specification

## Overview

`demo_listbox_static` demonstrates the basic `Listbox` widget with static in-memory items. It creates a list of 30 simple items and shows how to use custom keys.

## Architecture

- **Listbox**: Base widget class
- **ListboxItem**: Item class with content, pk, and data attributes
- **custom_keys**: Dict mapping key names to handler functions

## Usage

```bash
python demo_listbox_static.py --debug
```

## Command-line Arguments

| Argument | Description |
|----------|-------------|
| `--debug` | Enable debug output |

## Features

- Creates 30 `ListboxItem` objects programmatically
- Uses default `itemsperpage=20`
- Uses default `itemheight=1`
- Custom key 'e' to display item details

## Custom Keys

| Key | Action |
|-----|--------|
| E | Display current item's content, pk, and data, then return `ListboxResult("redraw")` |
| Enter | Select current item |
| Escape | Cancel selection |

## Key Handler Implementation

```python
def handle_e(listbox):
    item = listbox.currentitem
    io.echo(f"{{labelcolor}}Item: {{valuecolor}}{item.content}{{/all}}\n")
    io.echo(f"{{labelcolor}}pk: {{valuecolor}}{item.pk}{{/all}}\n")
    io.echo(f"{{labelcolor}}data: {{valuecolor}}{item.data}{{/all}}\n")
    io.echo(f"Press any key to continue...")
    io.getch(30)
    return ListboxResult("redraw")
```

The handler returns `ListboxResult("redraw")` to cause the listbox to redraw after displaying the item details.

## Color Configuration

Sets IO variables for listbox styling:
- `engine.menu.boxcharcolor`: Border character color
- `engine.menu.color`: General menu color
- `engine.menu.shadowcolor`: Shadow color
- `engine.menu.cursorcolor`: Cursor highlight color
- `engine.menu.boxcolor`: Box border color
- `engine.menu.titlecolor`: Title bar color
- `engine.menu.disableditemcolor`: Disabled item color
- `engine.menu.resultfailedcolor`: Failed result color
- `itemcolor`: Normal item color
- `currentitemcolor`: Highlighted item color
- `normalcolor`: Default text color
- `cic`: Current item color
- `labelcolor`: Label text color
- `valuecolor`: Value text color
