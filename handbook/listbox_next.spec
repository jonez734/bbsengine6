# listbox_next Module Specification

## Overview

`listbox_next` is a terminal-based UI widget for displaying and selecting items from a list. It provides keyboard navigation, pagination, and a curses-style presentation with borders and a title bar.

## Architecture

- **ListboxItem**: Represents a single item in the list; may be disabled (not selectable)
- **Listbox**: Main widget class managing the item list, cursor position, pagination, and user interaction
- **fetchitems()**: Returns items for current page (sliced from items passed to `__init__`); override in subclass for custom data sources

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `items` | List[ListboxItem] | List of items to display |
| `currentitem` | ListboxItem | Currently selected item |
| `currentindex` | int | Index of current item (0-indexed) |
| `curpage` | int | Current page number (0-indexed) |
| `pos` | int | Cursor position within current page |

## REQUIRES / PROVIDES

- REQUIRES: Nothing (standalone UI component)
- PROVIDES: Selected `ListboxItem` or `None` on cancel

## Dependencies

- Consumes: Terminal I/O via `bbsengine6.io.echo`, `bbsengine6.io.terminal`
- Produces: Selected item on confirmed selection

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| itemsperpage | int | 20 | Number of items (disabled or otherwise) visible per page |
| itemheight | int | 1 | Uniform height of each item in rows |
| BORDER_WIDTH | int | 4 | Horizontal border padding |
| title | str | "" | Title displayed at top of widget |
| GETCH_TIMEOUT | float | 0.25 | Key input timeout in seconds |
| idle | Optional[Callable[[], Optional[ListboxResult] | bool]] | None | Optional callback called when the key loop times out (getch returns None). Can return ListboxResult to exit, False to ring bell, or None/True to continue |
| custom_keys | Optional[dict[str, Callable[[], Optional[ListboxResult]]]] | None | Dict mapping key names (e.g., "KEY_INSERT", "KEY_DELETE") to callbacks. These are merged into `key_handlers` dict. Callback returns None to continue, or a ListboxResult to exit. Can also override standard keys (e.g., "KEY_UP", "KEY_DOWN") |

## key_handlers

The `key_handlers` dict maps key names to handler functions. Standard handlers are:

| Key | Handler Method |
|-----|----------------|
| KEY_ESC | `_handle_key_esc` |
| KEY_ENTER | `_handle_key_enter` |
| KEY_UP | `_handle_key_up` |
| KEY_DOWN | `_handle_key_down` |
| KEY_PAGEUP | `_handle_key_pageup` |
| KEY_PAGEDOWN | `_handle_key_pagedown` |
| KEY_HOME | `_handle_key_home` |
| KEY_END | `_handle_key_end` |

In the constructor, standard handlers are first populated, then `custom_keys` are merged via `key_handlers.update(custom_keys)`, allowing users to override standard key behavior.

## Current Item Color (cic)

The `itemcolors` dict determines the color used when rendering items:

```python
itemcolors = {
    "disabled": "{bggray}",
    "highlighted": "{bgwhite}{black}",
    "normal": "{normalcolor}",
}
```

When displaying each item:
- If item is disabled: use `itemcolors["disabled"]` and call `io.setvar("cic", itemcolors["disabled"])`
- If item is highlighted (current): use `itemcolors["highlighted"]` and call `io.setvar("cic", itemcolors["highlighted"])`
- Otherwise: use `itemcolors["normal"]` and call `io.setvar("cic", itemcolors["normal"])`

## Width Calculation

- `terminalwidth` = `terminal.width()`
- `contentwidth` = `terminal.width() - 3*2` (does not include borders)
- `totalwidth` = `contentwidth + 6` (content + left border + right border)
- `hline` = `f"{{hline:{contentwidth - 2}}}"` (computed in constructor)
- Left border: `" {vline} "` (3 chars)
- Right border: `" {vline} "` (3 chars)

The border consists of a space, vertical line, space (3 chars on each side).

## Height Calculation

- **Title box** (if title is given): 4 lines
  - Line 1: top border (`f" {{ulcorner}}{hline}{{urcorner}}"`)
  - Line 2: blank (`f" {{vline}}{' '*(contentwidth-2)}{{vline}}"`)
  - Line 3: title with left/right borders (`f" {{vline}}{title.center(contentwidth-2)}{{vline}}"`)
  - Line 4: blank (`f" {{vline}}{' '*(contentwidth-2)}{{vline}}"`)

- **Middle border** (between title box and content area): `_display_middle_border()`
  - Uses `{rtee}` and `{ltee}`: `f" {{rtee}}{hline}{{ltee}}"`

- **Top border** (if no title, displays instead of middle border): `_display_top_border()`
  - Uses `{ulcorner}` and `{urcorner}`: `f" {{ulcorner}}{hline}{{urcorner}}"`

- **Content area** (below middle border or top border):
  - Lines 1-n: items (`itemsperpage` lines, each item has `itemheight` rows)
  - Item display uses `{cic}` for color, `{/all}` before right border
  - When highlighted, item is drawn with `end=""` to keep cursor on same line
  - If fewer items than `itemsperpage`, pad with blank lines using `f" {{vline}} {' '*(contentwidth-4)} {{vline}}"`

- **Bottom border**: `_display_bottom_border()`
  - Uses `{llcorner}` and `{lrcorner}`: `f" {{llcorner}}{hline}{{lrcorner}}"`

Content height (not including borders) = itemsperpage × itemheight

> **Note**: `listbox_next` is a UI widget component, not a bbsengine6 module. It is exempt from the standard lifecycle functions (`detect`, `draw`, `init`, `buildargs`, `access`, `main`).

## Key Bindings

| Key | Action |
|-----|--------|
| Enter | Select current item, return it (if not disabled) |
| Escape | Cancel selection, return None |
| Up | Move to previous item (skip disabled) |
| Down | Move to next item (skip disabled, wrap to next page) |
| Page Up | Move to previous page |
| Page Down | Move to next page |
| Home | Jump to first selectable item |
| End | Jump to last selectable item |

## Disabled Items

A `ListboxItem` may have `disabled=True`. Disabled items:
- **Display** on the page normally (visible to user)
- **Cannot be highlighted** - cursor navigation skips over them

## Data Source

- Items passed to `__init__` are sliced by the base `fetchitems()` method to return only items for the current page
- Override `fetchitems()` in subclass to load items from a database cursor or other source

## Public API

```python
from typing import Any, Callable, List, NamedTuple, Optional

class ListboxItem:
    content: str
    pk: Any
    data: Any
    disabled: bool
    onkey: Optional[Callable[["ListboxItem", str], bool]] = None
    
    def handle_key(self, key: str) -> bool: ...

class ListboxResult(NamedTuple):
    status: str  # "selected" | "cancelled" | "noitems" | "custom"
    item: Optional[ListboxItem] = None
    data: Optional[dict] = None

class Listbox:
    def __init__(
        self,
        args,
        title: str = "",
        itemsperpage: int = 20,
        itemheight: int = 1,
        items: Optional[List[ListboxItem]] = None,
        idle: Optional[Callable[[], None]] = None,
        custom_keys: Optional[dict[str, Callable[[], Optional[ListboxResult]]]] = None,
        **kwargs,
    ) -> None: ...
    
    @property
    def currentitem(self) -> Optional[ListboxItem]: ...
    @property
    def currentindex(self) -> int: ...
    @property
    def curpage(self) -> int: ...
    
    def fetchitems(self) -> List[ListboxItem]: ...

    def onkey(self, ch: Optional[str]) -> Optional[ListboxResult] | bool: ...

    def run(self, prompt: str = "listbox_next: ") -> ListboxResult: ...

    key_handlers: dict[str, Callable[[], Optional[ListboxResult]]]

## Key Handler Methods

Each standard key has a corresponding private handler method:

| Method | Key | Description |
|--------|-----|-------------|
| `_handle_key_esc` | KEY_ESC | Returns `ListboxResult("cancelled")` |
| `_handle_key_enter` | KEY_ENTER | Returns `ListboxResult("selected", currentitem)` if item not disabled, else `False` |
| `_handle_key_up` | KEY_UP | Move to previous enabled item (skip disabled, wrap to prev page) |
| `_handle_key_down` | KEY_DOWN | Move to next enabled item (skip disabled, wrap to next page) |
| `_handle_key_pageup` | KEY_PAGEUP | Move to previous page |
| `_handle_key_pagedown` | KEY_PAGEDOWN | Move to next page |
| `_handle_key_home` | KEY_HOME | Jump to first enabled item on current page |
| `_handle_key_end` | KEY_END | Jump to last enabled item on current page |

> **Note**: All key handler methods MUST have docstrings describing their behavior. Update this spec when adding or modifying key handlers.

## run() Behavior

1. If there are no items to display:
   - Return `ListboxResult("noitems")`
2. Display the listbox (title box + content area)
3. Show the prompt
4. Echo `{savecursor}` to save cursor position
5. Enter a loop:
   ```
   while True:
       result = self.onkey(io.getch(GETCH_TIMEOUT))
       if isinstance(result, ListboxResult):
           return result
       if result is True:
           io.echo("{restorecursor}", end="", flush=True)
       elif result is False:
           io.echo("{BEL}", end="", flush=True)
   ```

## onkey() Method

Handles key input and returns `Optional[ListboxResult] | bool`:

- Returns `True` when a key was handled (cursor moved, etc.)
- Returns `False` when a key was not handled (caller will ring bell)
- Returns `ListboxResult` when selection is made or cancelled
- Returns `None` only for idle (continues loop)

- If `ch` is `None` and `idle` is a callable:
  - Call `idle()` and return its result if it's a `ListboxResult`
  - If `idle()` returns `False`, return `False` (rings bell)
  - Otherwise return `True` to continue
- `KEY_ESC`: Return `ListboxResult("cancelled")`
- `KEY_ENTER`:
  - If current item is not disabled:
    - Return `ListboxResult("selected", currentitem)`
  - Else (disabled):
    - Return `False`
- `KEY_UP`: 
  - If there is an item above the current highlight:
    - Cursor up to the current item line using `_cursor_moves_to_item()`
    - Redraw the current item as non-highlighted
    - Cursor up 1 line (`{cursorup}`)
    - Move up one item (skip any disabled items)
    - Draw the new item as highlighted
    - Return `True`
  - Else if there is a previous page:
    - Redraw current item as non-highlighted
    - Display previous page
    - Set highlighted item to last item on new page (skipping disabled)
    - Return `True`
  - Else (no previous items or previous pages):
    - Return `False`
- `KEY_DOWN`:
  - If there is an item below the current highlight:
    - Cursor up to the current item line
    - Redraw the current item as non-highlighted
    - Cursor down 1 line (`{cud}`)
    - Move down one item (skip any disabled items)
    - Draw the new item as highlighted
    - Return `True`
  - Else if there is a next page:
    - Redraw current item as non-highlighted
    - Display next page
    - Set highlighted item to first item on new page (skipping disabled)
    - Return `True`
  - Else (no next items or next pages):
    - Return `False`
- `KEY_PAGEUP`:
  - If there is a previous page:
    - Redraw current item as non-highlighted
    - Display previous page
    - Set highlighted item to first enabled item on new page
    - Return `True`
  - Else:
    - Return `False`
- `KEY_PAGEDOWN`:
  - If there is a next page:
    - Redraw current item as non-highlighted
    - Display next page
    - Set highlighted item to first enabled item on new page
    - Return `True`
  - Else:
    - Return `False`
- `KEY_HOME`:
  - If not already on the first enabled item:
    - Cursor up to the current item line using `_cursor_moves_to_item()`
    - Redraw the current item as non-highlighted
    - Cursor up `currentindex - first_idx` lines
    - Move to first enabled item on current page
    - Draw the new item as highlighted
  - Return `True`
- `KEY_END`:
  - If not already on the last enabled item:
    - Cursor up to the current item line using `_cursor_moves_to_item()`
    - Redraw the current item as non-highlighted
    - Cursor down `last_idx - current_idx` lines
    - Move to last enabled item on current page
    - Draw the new item as highlighted
  - Return `True`
- Any other key:
  - If `currentitem.onkey` is provided:
    - Call `currentitem.onkey(currentitem, key)` with the pressed key
    - If it returns True: return `True`
    - If it returns False: return `False`
  - If `currentitem.onkey` is not provided:
    - Return `False`

### Idle Callback

See `onkey()` method - `idle` is called when `ch` is `None`. The `idle` callback can return:
- `None`/nothing → continues (returns `True`)
- `ListboxResult` → exits loop
- `False` → rings bell (returns `False`)

### OnKey Callback

The `onkey` attribute on `ListboxItem` is a callable taking `item: ListboxItem` and `key: str`, returning `bool`:
- Called when a key is pressed that is not one of the standard navigation keys (Enter, Escape, Up, Down, Page Up, Page Down, Home, End)
- The callback receives the currently selected item and the key that was pressed
- Return `True` if the key was handled (no bell rings)
- Return `False` if the key was not handled (bell rings)
- Example uses: 'e' to edit an item, 'd' to delete, 'r' to refresh
```

See [BESTPRACTICE.spec](BESTPRACTICE.spec) for additional best practices.
