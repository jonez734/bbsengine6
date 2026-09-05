# bbsengine6.listbox — scrollable list widget

> **Status:** canonical. The widget lives at
> `py/src/bbsengine6/listbox.py`. `handbook/listbox.md` is the
> older user-facing reference (with `Op` instead of
> `ListboxResult`, `keyhandler` instead of `custom_keys`); this
> spec is the single source of truth for the live API.

`bbsengine6.listbox` is a paginated, curses-style TUI listbox with
keyboard navigation, item highlighting, idle callbacks, and
per-item key handlers. It is the building block for every
interactive BBS prompt (member pickers, blurb lists, channel
browser, etc.).

## Contents

- [Classes](#classes)
- [Constructor](#constructor)
- [Public API](#public-api)
- [Configuration](#configuration)
- [Key handlers](#key-handlers)
- [Item colors](#item-colors)
- [Width and height math](#width-and-height-math)
- [`run()` lifecycle](#run-lifecycle)
- [`onkey()` semantics](#onkey-semantics)
- [Multi-column (future)](#multi-column-future)

## Classes

| Class         | Purpose                                                                                              |
|---------------|------------------------------------------------------------------------------------------------------|
| `ListboxItem` | Single row in the list. Carries `content`, `pk`, `data`, `disabled`, optional `onkey` callback       |
| `ListboxResult` | `NamedTuple(status, item=None, data=None)`. `status` is one of `"selected"`, `"cancelled"`, `"noitems"`, `"redraw"`, `"custom"` |
| `Listbox`     | Main widget. Holds `items`, `currentitem`, `currentindex`, `curpage`, `pos`, the `key_handlers` dict, and the `prompt` string |
| `ListboxCursor` | Helper class (see `py/src/bbsengine6/listboxcursor.py`) for cursor positioning math               |

## Constructor

```python
Listbox(
    args: Any,
    title: str = "",
    itemsperpage: int = 20,
    itemheight: int = 1,
    items: Optional[List[ListboxItem]] = None,
    idle: Optional[Callable[[], Optional[ListboxResult] | bool]] = None,
    custom_keys: Optional[Dict[str, Callable[[], Optional[ListboxResult]]]] = None,
    **kwargs,
) -> None
```

`args` is the application's `argparse.Namespace` (used for `args.debug`
gates). The standard handlers are populated first; `custom_keys`
are merged in via `key_handlers.update(custom_keys)`, so callers
can override standard keys (`"KEY_UP"`, `"KEY_DOWN"`, …) by
passing the same key name.

## Public API

| Member                       | Type                                                              | Notes                                                        |
|------------------------------|-------------------------------------------------------------------|--------------------------------------------------------------|
| `items`                      | `List[ListboxItem]`                                               | Full list passed in `__init__`                               |
| `currentitem`                | property → `Optional[ListboxItem]`                                | Currently selected item                                      |
| `currentindex`               | property → `int`                                                  | Index into the current page (0-based)                        |
| `curpage`                    | property → `int`                                                  | Current page (0-based)                                       |
| `pos`                        | `int`                                                             | Cursor position within the current page                      |
| `prompt`                     | `str`                                                             | Set inside `run(prompt)`                                     |
| `key_handlers`               | `Dict[str, Callable[[], bool | Optional[ListboxResult]]]`         | Effective key → handler mapping                              |
| `fetchitems() -> List[ListboxItem]` | method                                                   | Returns items for the current page; override in subclass     |
| `_highlight_item(idx)`       | method                                                            | Repaints item at `idx` as highlighted                         |
| `onkey(ch) -> Optional[ListboxResult] | bool` | method                                              | Dispatch a keypress                                           |
| `run(prompt) -> ListboxResult` | method                                                         | Drive the widget loop                                         |

## Configuration

| Field                       | Type          | Default | Description                                                       |
|-----------------------------|---------------|---------|-------------------------------------------------------------------|
| `itemsperpage`              | `int`         | 20      | Number of items per page (disabled or otherwise)                  |
| `itemheight`                | `int`         | 1       | Uniform height of each item in rows                               |
| `GETCH_TIMEOUT`             | `float`       | 0.25    | Key input timeout in seconds                                      |
| `BOTTOM_BORDER_HEIGHT`      | `int`         | 1       | Height of the bottom border line                                  |
| `CONTENT_PADDING`           | `int`         | 4       | Horizontal padding for item content (borders + spacing)           |
| `BORDER_WIDTH_LEFT`         | `int`         | 3       | Left border width                                                 |
| `BORDER_WIDTH_RIGHT`        | `int`         | 3       | Right border width                                                |
| `BORDER_CORNER_WIDTH`       | `int`         | 2       | Width reduction for border lines (space + vline each side)        |
| `title`                     | `str`         | `""`    | Title displayed at top of widget                                  |
| `idle`                      | callable      | `None`  | Called on idle keypress; see [onkey() semantics](#onkey-semantics) |
| `custom_keys`               | `Dict[str, Callable[[], Optional[ListboxResult]]]` | `None` | Merged into `key_handlers` after the standard handlers |

`note: listbox_next` is a UI widget component, not a bbsengine6
module. It is exempt from the standard lifecycle functions
(`detect`, `draw`, `init`, `buildargs`, `access`, `main`).

## Key handlers

| Key              | Method               | Action                                                                 |
|------------------|----------------------|------------------------------------------------------------------------|
| `KEY_ESC`        | `_handle_key_esc`    | Returns `ListboxResult("cancelled")`                                  |
| `KEY_ENTER`      | `_handle_key_enter`  | Returns `ListboxResult("selected", currentitem)`; `False` if disabled  |
| `KEY_UP`         | `_handle_key_up`     | Previous enabled item (skip disabled; wrap to previous page)           |
| `KEY_DOWN`       | `_handle_key_down`   | Next enabled item (skip disabled; wrap to next page)                  |
| `KEY_PAGEUP`     | `_handle_key_pageup` | Previous page                                                          |
| `KEY_PAGEDOWN`   | `_handle_key_pagedown` | Next page                                                           |
| `KEY_HOME`       | `_handle_key_home`   | First enabled item on the current page                                 |
| `KEY_END`        | `_handle_key_end`    | Last enabled item on the current page                                  |

`custom_keys` entries are merged on top of the standard handlers,
so a caller can override `"KEY_UP"` / `"KEY_DOWN"` by passing the
same key in `custom_keys`.

## Item colors

The `itemcolors` dict determines per-item color:

```python
itemcolors = {
    "disabled":   "{bggray}",
    "highlighted": "{bgwhite}{black}",
    "normal":     "{normalcolor}",
}
```

Render logic:

- Disabled item → `itemcolors["disabled"]`; `io.setvar("cic", itemcolors["disabled"])`.
- Highlighted item → `itemcolors["highlighted"]`; `io.setvar("cic", itemcolors["highlighted"])`.
- Otherwise → `itemcolors["normal"]`; `io.setvar("cic", itemcolors["normal"])`.

## Width and height math

```
terminalwidth = terminal.width()
contentwidth  = terminalwidth - BORDER_WIDTH_LEFT - BORDER_WIDTH_RIGHT
totalwidth    = contentwidth + BORDER_WIDTH_LEFT + BORDER_WIDTH_RIGHT
hline         = "{hline:" + str(contentwidth - BORDER_CORNER_WIDTH) + "}"
```

Left border: `" {vline} "` (BORDER_WIDTH_LEFT chars). Right border:
same shape, BORDER_WIDTH_RIGHT chars. The asymmetric border widths
let a caller intentionally bias left vs right content.

Border layout:

- **Title box** (when `title` is set): 4 lines — top border, blank,
  centered title, blank.
- **Middle border** (between title box and content when title is
  set): `_display_middle_border()` — `"{rtee}{hline}{ltee}"`.
- **Top border** (when no title): `_display_top_border()` —
  `"{ulcorner}{hline}{urcorner}"`.
- **Content area**: `itemsperpage` lines, each item rendered with
  `itemheight` rows. `{cic}` is the color; `{/all}` resets before
  the right border. Fewer items than `itemsperpage` → padded with
  blank lines.
- **Bottom border**: `_display_bottom_border()` — `"{llcorner}{hline}{lrcorner}"`.

Content height (excluding borders) = `itemsperpage × itemheight`.

## `run()` lifecycle

```python
def run(self, prompt: str) -> ListboxResult:
    if not self.items:
        return ListboxResult("noitems")
    self.prompt = prompt
    self._display()
    io.echo(f"{{savecursor}} {promptcolor}{prompt}{{cha}}", end="", flush=True)
    while True:
        result = self.onkey(io.getch(GETCH_TIMEOUT))
        if isinstance(result, ListboxResult):
            if result.status == "redraw":
                # full redraw (title + content + borders + prompt)
                ...
                continue
            return result
        if result is True:
            io.echo("{restorecursor}", end="", flush=True)
        elif result is False:
            io.echo("{BEL}", end="", flush=True)
```

`ListboxResult("redraw")` is a request from a key handler for a
complete refresh (title box, content, borders, prompt). The current
item selection is preserved across a redraw.

## `onkey()` semantics

`onkey(ch) -> Optional[ListboxResult] | bool`

- `True` — key was handled; loop continues.
- `False` — key was not handled; caller rings the bell.
- `ListboxResult` — selection made or cancelled; loop exits.
- `None` — only returned when `ch is None` and no `idle` callback
  is set; loop continues.

If `ch is None` and `idle` is callable:

- `idle()` returns `ListboxResult` → returned as the loop result.
- `idle()` returns `False` → `onkey` returns `False` (bell rings).
- otherwise → `onkey` returns `True` (continue).

For non-standard keys, `onkey` delegates to
`currentitem.onkey(currentitem, key)`. The callback returns `True`
(key handled) or `False` (key not handled → bell). Common uses:
`'e'` for edit, `'d'` for delete, `'r'` for refresh.

## Multi-column (future)

`bbsengine6/listbox_feature_multicolumn.md` describes a multi-column
layout extension:

- column count of at least one, with "as many as fit" opt-in
- column width = `max(rendered_length(item)) + 1` for that column
- single column → unchanged behavior (each item fills the row)
- two or more columns:
  - `KEY_DOWN` at the bottom of a column → next column's item 0
  - last item on last column → next page (bell if no next page)
  - `KEY_RIGHT` / `KEY_LEFT` move to the column to the right/left
    (with wrap); row is preserved
  - `KEY_END` → last item of current column
  - `KEY_HOME` → first item of current column

The multi-column layout is not yet implemented in
`bbsengine6.listbox`. The single-column widget above is the only
live surface.
