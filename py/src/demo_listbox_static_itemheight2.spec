# demo_listbox_static_itemheight2 Specification

## Overview

`demo_listbox_static_itemheight2` demonstrates the `Listbox` widget with `itemheight=2`, showing how to display multi-line items. Each item displays two lines: a demo number and a NATO phonetic code.

## Architecture

- **Listbox**: Base widget class with `itemheight=2`
- **ListboxItem**: Item class with multi-line content (contains `\n`)
- **custom_keys**: Dict mapping key names to handler functions

## Usage

```bash
python demo_listbox_static_itemheight2.py --debug
```

## Command-line Arguments

| Argument | Description |
|----------|-------------|
| `--debug` | Enable debug output |

## Features

- Creates 28 `ListboxItem` objects programmatically
- Uses `itemsperpage=5`
- Uses `itemheight=2` (each item takes 2 lines)
- Multi-line content using `\n` in the content string
- NATO phonetic alphabet codes for second line content

## Custom Keys

| Key | Action |
|-----|--------|
| E | Display current item's content, pk, and data, then return `ListboxResult("redraw")` |
| Enter | Select current item |
| Escape | Cancel selection |

## Item Content Format

Each item has content in the format:
```
demo item #N
<NATO_CODE>
```

Where NATO_CODE cycles through: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, india, juliet, kilo, lima, mike, november, oscar, papa, quebec, romeo, sierra, tango, uniform, victor, whiskey, xray, yankee, zulu

## Height Calculation

With `itemheight=2`:
- Content area height = itemsperpage × itemheight = 5 × 2 = 10 lines
- Each item displays on 2 consecutive lines
- The listbox scrolls by item, not by line

## Key Handler Implementation

Same as `demo_listbox_static`:
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

Same color configuration as `demo_listbox_static`.

See [demo_listbox_static.spec](demo_listbox_static.spec) for color details.
