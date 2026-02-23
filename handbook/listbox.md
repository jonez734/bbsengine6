listbox
======

A paginated listbox widget for terminal-based UI.

Overview
--------

The listbox provides a scrollable, paginated list with keyboard navigation.
It uses a database cursor to fetch items page-by-page for efficient memory
usage with large datasets.

Classes
-------

### Op (NamedTuple)

Result of a listbox operation.

- **kind**: str - Operation type: "select", "exit", "help", "refresh", "noitems", "unknown"
- **listitem**: Optional[Any] - The selected item or None

### ListboxItem

Base class for listbox items. Subclass to implement custom items.

**Class Constants:**
- `WIDTH_OVERHEAD: int = 9` - Width overhead for box characters and spacing

**Attributes:**
- `status: str` - Item status string
- `label: str` - Display label for the item (supports `\n` for multi-line)
- `itemid: Optional[Any]` - Unique identifier for the item
- `pk: Any` - Primary key (defaults to counter value)
- `rec: dict[str, Any]` - Raw record data from database
- `width: int` - Display width
- `height: int` - Display height (for multi-line items)

**Class Methods:**

- `compose(cls, rec: dict[str, Any], counter: int) -> dict[str, Any]` - Transform raw database record into display-ready data. Returns `{"label": str, "height": int}`. Override in subclass.

**Methods:**

- `help() -> None` - Display help for this item. Override in subclass.
- `display() -> None` - Render the item to the terminal. Splits label on `\n` and pads each line.

### Listbox

Main listbox widget.

**Constructor Parameters:**
- `args: Any` - Application arguments (must have `.debug` attribute)
- `title: str` - Listbox title (default: "")
- `pagesize: int` - Number of items per page (default: 20)
- `itemheight: int` - Height of each item (default: 1, for uniform height)
- `keyhandler: Optional[Callable[[Any, str, Listbox], Any]]` - Custom key handler
- `itemclass: Optional[type[ListboxItem]]` - Class to instantiate for items
- `data: Optional[list[Any]]` - List of records (alternative to database cursor)
- `**kwargs: Any` - Additional arguments passed to itemclass

**Attributes:**
- `args: Any` - Application arguments
- `page: int` - Current page number (0-indexed)
- `curpos: int` - Current cursor position within page (0-based index into items)
- `pagesize: int` - Items per page
- `itemheight: int` - Uniform height per item
- `items: list[ListboxItem]` - Current page items
- `title: str` - Listbox title
- `currentitem: Optional[ListboxItem]` - Currently selected item
- `keyhandler: Optional[Callable]` - Custom key handler
- `totalitems: int` - Total items in dataset
- `terminalwidth: int` - Terminal width
- `itemclass: Optional[type[ListboxItem]]` - Item class
- `numpages: int` - Total pages (ceil(totalitems/pagesize))
- `numitems: int` - Items on current page
- `positionheight: int` - Visual cursor position: `itemheight * curpos`

**Properties:**
- `pageheight: int` - Total visual height of page: `numitems * itemheight`

**Methods:**

- `fetchpage() -> Optional[list[ListboxItem]]` - Fetch current page from database
- `displayitems() -> None` - Render current page items
- `display() -> None` - Render complete listbox UI (box + items)
- `handle(prompt: str = "listbox: ") -> Op | bool | None` - Handle keyboard input
- `run(prompt: str = "listbox: ") -> Optional[Op]` - Main loop: display + handle

Keyboard Navigation
--------------------

| Key           | Action                                      |
|---------------|---------------------------------------------|
| KEY_DOWN      | Move cursor down one item                   |
| KEY_UP        | Move cursor up one item                     |
| KEY_HOME      | Jump to first item                          |
| KEY_END       | Jump to last item                           |
| KEY_PAGEDOWN  | Next page                                   |
| KEY_PAGEUP    | Previous page                               |
| KEY_ENTER     | Select current item                         |
| KEY_ESC       | Exit without selection                      |
| X             | Exit without selection                      |
| ? or KEY_HELP | Request help for current item              |

Custom Key Handler
------------------

The `keyhandler` callable receives `(args, ch, listbox)` and should return:
- `False` - Bell/error, keep waiting for input
- `True` - Key was handled, continue waiting
- An `Op` - Return immediately with that operation

Example:

```python
def my_keyhandler(args, ch, lb):
    if ch == "a":
        return Op("select", lb.items[0])
    return False
```

Display Format
--------------

The listbox renders as an ASCII box:

```
┌─ Title ────────────────────────────────────────┐
│ ▌item #1                                  │░│
│ │item #2                                  │░│
│ │item #3                                  │░│
│ │item #4                                  │░│
│ └─────────────────────────────────────────────┘
  ████████
```

Current item uses `{var:currentitemcolor}`, others use `{var:itemcolor}`.

Dependencies
------------

- `bbsengine6.io` - Terminal I/O
- `bbsengine6.screen` - Screen positioning
