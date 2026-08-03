from math import ceil
from typing import Any, Callable, List, NamedTuple, Optional

from . import io  # type: ignore
from .io.echo import rendered_length


class ListboxItem:
    content: str
    pk: Any
    data: Any
    disabled: bool
    hotkey: str
    onkey: Optional[Callable[["ListboxItem", str], bool]] = None
    display: Optional[Callable[["ListboxItem", "Listbox", bool], None]] = None

    def __init__(
        self,
        content: str = "",
        pk: Any = None,
        data: Any = None,
        disabled: bool = False,
        hotkey: str = "",
        onkey: Optional[Callable[["ListboxItem", str], bool]] = None,
        display: Optional[Callable[["ListboxItem", "Listbox", bool], None]] = None,
        **kwargs: Any,
    ) -> None:
        self.content = content
        self.pk = pk
        self.data = data
        self.disabled = disabled
        self.hotkey = hotkey
        self.onkey = onkey
        self.display = display

    def handle_key(self, key: str) -> bool:
        return False


class ListboxResult(NamedTuple):
    status: str
    item: Optional[ListboxItem] = None
    data: Optional[dict] = None


class Listbox:
    GETCH_TIMEOUT = 0.25
    LISTBOX_ONKEY_BUFFER_LEN = 5
    BOTTOM_BORDER_HEIGHT = 1
    CONTENT_PADDING = 4
    BORDER_WIDTH_LEFT = 3
    BORDER_WIDTH_RIGHT = 3
    BORDER_CORNER_WIDTH = 2
    TITLE_BOX_HEIGHT = 2
    MIDDLE_BORDER_HEIGHT = 1
    TOP_BORDER_HEIGHT = 1

    def __init__(
        self,
        args: Any,
        title: str = "",
        itemsperpage: int = 20,
        itemheight: int = 1,
        items: Optional[List[ListboxItem]] = None,
        idle: Optional[Callable[[], None]] = None,
        custom_keys: Optional[dict[str, Callable[[], Optional[ListboxResult]]]] = None,
        hotkeys: Optional[dict[str, Callable[[], Optional[ListboxResult]]]] = None,
        itemclass: Optional[type] = None,
        **kwargs: Any,
    ) -> None:
        self.args = args
        self.title = title
        self.itemsperpage = itemsperpage
        self.itemheight = itemheight
        self.items = items if items is not None else []
        self.idle = idle
        self.custom_keys = custom_keys if custom_keys else {}
        self.hotkeys = hotkeys if hotkeys else {}
        self.kwargs = kwargs
        self.itemclass = itemclass

        self._curpage = 0
        self._currentindex = 0
        self._key_buffer: str = ""
        self._hotkey_map: dict[str, ListboxItem] = {}
        self._build_hotkey_map()

        self.terminalwidth = io.terminal.width()  # type: ignore
        self.contentwidth = (
            self.terminalwidth - self.BORDER_WIDTH_LEFT - self.BORDER_WIDTH_RIGHT
        )
        ##        logentry(
        ##            f"{self.contentwidth=} {self.terminalwidth=} {self.BORDER_WIDTH_LEFT=} {self.BORDER_WIDTH_RIGHT=}",
        ##            level="debug",
        ##        )
        self.totalwidth = (
            self.contentwidth + self.BORDER_WIDTH_LEFT + self.BORDER_WIDTH_RIGHT
        )
        self.hline = f"{{hline:{self.contentwidth + self.BORDER_CORNER_WIDTH}}}"

        self.numpages = max(1, int(ceil(len(self.items) / self.itemsperpage)))

        self.key_handlers: dict[str, Callable[[], bool | Optional[ListboxResult]]] = {
            "KEY_ESC": self._handle_key_esc,
            "KEY_ENTER": self._handle_key_enter,
            "KEY_UP": self._handle_key_up,
            "KEY_DOWN": self._handle_key_down,
            "KEY_PAGEUP": self._handle_key_pageup,
            "KEY_PAGEDOWN": self._handle_key_pagedown,
            "KEY_HOME": self._handle_key_home,
            "KEY_END": self._handle_key_end,
            "KEY_FF": self._handle_key_ff,
        }
        if self.custom_keys:
            self.key_handlers.update(self.custom_keys)

    def _build_hotkey_map(self) -> None:
        self._hotkey_map = {}
        for item in self.items:
            if hasattr(item, "hotkey") and item.hotkey:
                self._hotkey_map[item.hotkey] = item

    def _navigate_to_item(self, item: ListboxItem) -> bool:
        try:
            item_index = self.items.index(item)
        except ValueError:
            return False
        target_page = item_index // self.itemsperpage
        if target_page != self._curpage:
            self._curpage = target_page
            self._redraw_content_area()
        self._currentindex = item_index % self.itemsperpage
        return True

    @property
    def currentitem(self) -> Optional[ListboxItem]:
        page_items = self.fetchitems()
        if page_items and self._currentindex < len(page_items):
            return page_items[self._currentindex]
        return None

    @property
    def currentindex(self) -> int:
        return self._currentindex

    @property
    def curpage(self) -> int:
        return self._curpage

    @property
    def pos(self) -> int:
        return self._curpage * self.itemsperpage + self._currentindex

    def fetchitems(self) -> List[ListboxItem]:
        start = self._curpage * self.itemsperpage
        end = start + self.itemsperpage
        return self.items[start:end]

    def _get_all_items(self) -> List[ListboxItem]:
        return self.items

    def _get_first_enabled_index(self, items: List[ListboxItem], start: int = 0) -> int:
        for i in range(start, len(items)):
            if not items[i].disabled:
                return i
        return -1

    def _get_last_enabled_index(self, items: List[ListboxItem]) -> int:
        for i in range(len(items) - 1, -1, -1):
            if not items[i].disabled:
                return i
        return -1

    def _get_next_enabled_index(self, items: List[ListboxItem], current: int) -> int:
        for i in range(current + 1, len(items)):
            if not items[i].disabled:
                return i
        return -1

    def _get_prev_enabled_index(self, items: List[ListboxItem], current: int) -> int:
        for i in range(current - 1, -1, -1):
            if not items[i].disabled:
                return i
        return -1

    def _display_item(self, item: ListboxItem, highlighted: bool = False) -> None:
        display_method = getattr(item, "display", None)
        if display_method is None:
            display_method = getattr(type(item), "display", None)
        ##        logentry(f"_display_item.200: checking for item.display {display_method=}", level="debug")
        if display_method is not None and callable(display_method):
            ##            logentry("_display_item.100: calling item.display()", level="debug")
            display_method(item, self, highlighted)
            return

        if item.disabled:
            io.setvar("cic", "{listbox.item.disabled}")
        elif highlighted:
            io.setvar("cic", "{listbox.item.highlighted}")
        else:
            io.setvar("cic", "{listbox.item.normal}")

        lines = item.content.split("\n")
        for line_num in range(self.itemheight):
            if line_num < len(lines):
                line = lines[line_num]
            else:
                line = ""
            visible_len = rendered_length(line)
            ##            logentry(f"{visible_len=} {self.contentwidth=} {line=}", level="debug")
            ##            if visible_len > self.contentwidth:
            ##                truncated = ""
            ##                for i, ch in enumerate(line):
            ##                    if rendered_length(truncated + ch + "...") <= self.contentwidth:
            ##                        truncated += ch
            ##                    else:
            ##                        break
            ##                padded = truncated + "..."
            ##            else:
            padded = line + " " * (self.contentwidth - visible_len)
            io.echo(
                f" {{/all}}{{listbox.boxcolor}}{{vline}} {{cic}}{padded} {{/all}}{{listbox.boxcolor}}{{vline}}",
                wordwrap=False,
            )

    def _display_blank_line(self) -> None:
        for _ in range(self.itemheight):
            io.echo(
                f" {{/all}}{{listbox.boxcolor}}{{vline}} {' ' * self.contentwidth} {{listbox.boxcolor}}{{vline}}",
                wordwrap=False,
            )

    def _display_title_box(self) -> None:
        io.echo(
            f"{{/all}} {{listbox.boxcolor}}{{ulcorner}}{self.hline}{{listbox.boxcolor}}{{urcorner}}"
        )
        width = self.contentwidth
        centered = self.title.center(width)
        io.echo(
            f" {{/all}}{{listbox.boxcolor}}{{vline}} {{listbox.titlecolor}}{centered}{{/all}} {{listbox.boxcolor}}{{vline}}{{/all}}"
        )

    def _display_middle_border(self) -> None:
        io.echo(
            f" {{/all}}{{listbox.boxcolor}}{{rtee}}{self.hline}{{listbox.boxcolor}}{{ltee}}"
        )

    def _display_top_border(self) -> None:
        io.echo(
            f" {{/all}}{{listbox.boxcolor}}{{ulcorner}}{self.hline}{{listbox.boxcolor}}{{urcorner}}"
        )

    def _display_bottom_border(self) -> None:
        io.echo(
            f" {{/all}}{{listbox.boxcolor}}{{llcorner}}{self.hline}{{listbox.boxcolor}}{{lrcorner}}"
        )

    def _display(self) -> None:
        if self.title:
            self._display_title_box()
            self._display_middle_border()
        else:
            self._display_top_border()

        page_items = self.fetchitems()
        for i in range(self.itemsperpage):
            if i < len(page_items):
                if i == self._currentindex:
                    self._display_item(page_items[i], highlighted=True)
                else:
                    self._display_item(page_items[i], highlighted=False)
            else:
                self._display_blank_line()

        self._display_bottom_border()

    def _highlight_item(self, item_index: int) -> None:
        """Highlight the item at item_index on current page."""
        page_items = self.fetchitems()
        if item_index < len(page_items):
            if item_index != self._currentindex:
                self._position_from_prompt(item_index)
            self._display_item(page_items[item_index], highlighted=True)
            io.echo("{restorecursor}", end="", flush=True)

    def _redraw_content_area(self) -> None:
        io.echo(
            f"{{cursorup:{self.itemsperpage * self.itemheight + 1}}}",
            end="",
            flush=True,
        )
        page_items = self.fetchitems()
        for i in range(self.itemsperpage):
            if i < len(page_items):
                highlighted = i == self._currentindex
                self._display_item(page_items[i], highlighted=highlighted)
            else:
                self._display_blank_line()

    def _position_from_prompt(self, item_index: int) -> None:
        """Position cursor from prompt line to item at item_index on page."""
        cursor_up = self._cursor_moves_to_item(item_index)
        io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)

    def _handle_key_esc(self) -> Optional[ListboxResult]:
        """Handle KEY_ESC - cancel selection and return cancelled result."""
        return ListboxResult("cancelled")

    def _handle_key_enter(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_ENTER - select current item and return selected result."""
        if self.currentitem is not None and not self.currentitem.disabled:
            return ListboxResult("selected", self.currentitem)
        return False

    def _handle_key_up(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_UP - move to previous enabled item.

        If there is an item above, move cursor up and highlight it.
        If on first item of page, wrap to previous page.
        If already on first item of first page, ring bell and return None.
        """
        page_items = self.fetchitems()
        prev_idx = self._get_prev_enabled_index(page_items, self._currentindex)
        if prev_idx != -1:
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=False)
            diff = (self._currentindex + 1) - prev_idx
            cursor_up = diff * self.itemheight
            io.echo(f"{{cursorup:{cursor_up}}}{{cha}}", end="", flush=True)
            self._currentindex = prev_idx
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        elif self._curpage > 0:
            self._curpage -= 1
            page_items = self.fetchitems()
            last_idx = self._get_last_enabled_index(page_items)
            if last_idx != -1:
                self._currentindex = last_idx
            io.echo("{restorecursor}", end="", flush=True)
            self._redraw_content_area()
            io.echo("{restorecursor}", end="", flush=True)
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        else:
            io.echo("{BEL}", end="", flush=True)
            return None

    def _handle_key_down(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_DOWN - move to next enabled item.

        If there is an item below, move cursor down and highlight it.
        If on last item of page, wrap to next page.
        If already on last item of last page, ring bell and return None.
        """
        page_items = self.fetchitems()
        next_idx = self._get_next_enabled_index(page_items, self._currentindex)
        if next_idx != -1:
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=False)
            io.echo("{cha}", end="", flush=True)
            self._currentindex = next_idx
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        elif self._curpage < self.numpages - 1:
            self._curpage += 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            io.echo("{restorecursor}", end="", flush=True)
            self._redraw_content_area()
            io.echo("{restorecursor}", end="", flush=True)
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        else:
            io.echo("{BEL}", end="", flush=True)
            return None

    def _handle_key_pageup(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_PAGEUP - move to previous page.

        If not on first page, decrement page and highlight first enabled item.
        If already on first page, jump to first item on page.
        """
        if self._curpage > 0:
            self._curpage -= 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            io.echo("{restorecursor}", end="", flush=True)
            self._redraw_content_area()
            io.echo("{restorecursor}", end="", flush=True)
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        else:
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1 and self._currentindex != first_idx:
                self._currentindex = first_idx
                io.echo("{restorecursor}", end="", flush=True)
                self._redraw_content_area()
                io.echo("{restorecursor}", end="", flush=True)
                self._position_from_prompt(self._currentindex)
                self._display_item(page_items[self._currentindex], highlighted=True)
            else:
                io.echo("{BEL}", end="", flush=True)
            return True

    def _handle_key_pagedown(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_PAGEDOWN - move to next page.

        If not on last page, increment page and highlight first enabled item.
        If already on last page, jump to last item on page.
        """
        if self._curpage < self.numpages - 1:
            self._curpage += 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            io.echo("{restorecursor}", end="", flush=True)
            self._redraw_content_area()
            io.echo("{restorecursor}", end="", flush=True)
            self._position_from_prompt(self._currentindex)
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        else:
            page_items = self.fetchitems()
            last_idx = self._get_last_enabled_index(page_items)
            if last_idx != -1 and self._currentindex != last_idx:
                self._currentindex = last_idx
                io.echo("{restorecursor}", end="", flush=True)
                self._redraw_content_area()
                io.echo("{restorecursor}", end="", flush=True)
                self._position_from_prompt(self._currentindex)
                self._display_item(page_items[self._currentindex], highlighted=True)
            else:
                io.echo("{BEL}", end="", flush=True)
            return True

    def _handle_key_home(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_HOME - jump to first enabled item on current page.

        Moves highlight to the first enabled item on the current page.
        If already on first enabled item, does nothing but still returns True.
        """
        page_items = self.fetchitems()
        first_idx = self._get_first_enabled_index(page_items)
        if first_idx != -1 and self._currentindex != first_idx:
            old_idx = self._currentindex
            cursor_up = self._cursor_moves_to_item(old_idx)
            io.echo(f"{{cursorup:{cursor_up}}}{{cha}}", end="", flush=True)
            self._display_item(page_items[old_idx], highlighted=False)
            io.echo("{cha}", end="", flush=True)
            diff = (old_idx - first_idx + 1) * self.itemheight
            io.echo(f"{{cursorup:{diff}}}{{cha}}", end="", flush=True)
            self._currentindex = first_idx
            self._display_item(page_items[first_idx], highlighted=True)
        return True

    def _handle_key_end(self) -> bool | Optional[ListboxResult]:
        """Handle KEY_END - jump to last enabled item on current page.

        Moves highlight to the last enabled item on the current page.
        If already on last enabled item, does nothing but still returns True.
        """
        page_items = self.fetchitems()
        last_idx = self._get_last_enabled_index(page_items)
        if last_idx != -1 and self._currentindex != last_idx:
            old_idx = self._currentindex
            cursor_up = self._cursor_moves_to_item(old_idx)
            io.echo(f"{{cursorup:{cursor_up}}}{{cha}}", end="", flush=True)
            self._display_item(page_items[old_idx], highlighted=False)
            io.echo("{cha}", end="", flush=True)
            # +1 accounts for the cursor sitting one row below the item line
            # after the unhighlight redraw, matching the _handle_key_home math.
            diff = (last_idx - old_idx + 1) * self.itemheight
            io.echo(
                f"{{cursordown:{diff}}}{{cha}}", end="", flush=True
            )
            self._currentindex = last_idx
            self._display_item(page_items[last_idx], highlighted=True)
        return True

    def _handle_key_ff(self) -> ListboxResult:
        """Handle KEY_FF - full redraw of the listbox."""
        return ListboxResult("redraw")

    def onkey(self, ch: Optional[str]) -> Optional[ListboxResult] | bool:
        if ch == "KEY_ESC":
            self._key_buffer = ""
            return ListboxResult("cancelled")

        if ch is None:
            if self._key_buffer:
                return True
            if self.idle is not None and callable(self.idle):
                result = self.idle()
                if isinstance(result, ListboxResult):
                    return result
                if result is False:
                    return False
            return True

        if ch in self.key_handlers:
            result = self.key_handlers[ch]()
            if result is not None:
                return result
            return True

        self._key_buffer += ch
        if len(self._key_buffer) > self.LISTBOX_ONKEY_BUFFER_LEN:
            self._key_buffer = self._key_buffer[1:]

        if self._key_buffer in self._hotkey_map:
            matched_item = self._hotkey_map[self._key_buffer]
            if self._navigate_to_item(matched_item):
                if matched_item.onkey:
                    matched_item.onkey(matched_item, self._key_buffer)
                self._key_buffer = ""
                return True
            self._key_buffer = ""

        if self.currentitem is not None and callable(self.currentitem.onkey):
            if self.currentitem.onkey(self.currentitem, ch):
                return True
            else:
                return False

        return False

    def _cursor_moves_to_item(self, item: int) -> int:
        return (self.itemsperpage - item) * self.itemheight + 1

    def run(self, prompt: str) -> ListboxResult:
        if not self.items and not getattr(self, "_lazy_load", False):
            return ListboxResult("noitems")

        self.prompt = prompt

        self._display()
        io.echo(f"{{savecursor}} {{promptcolor}}{prompt}{{cha}}", end="", flush=True)

        cursor_up = self._cursor_moves_to_item(self._currentindex)
        ##        logentry(f"{cursor_up=}", level=logging.DEBUG)
        io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)

        page_items = self.fetchitems()
        if self._currentindex < len(page_items):
            self._display_item(page_items[self._currentindex], highlighted=True)

        io.echo("{restorecursor}", end="", flush=True)

        while True:
            result = self.onkey(io.getch(self.GETCH_TIMEOUT, **self.kwargs))
            if isinstance(result, ListboxResult):
                if result.status == "redraw":
                    self._display()
                    io.echo(
                        f"{{savecursor}} {{promptcolor}}{self.prompt}{{cha}}",
                        end="",
                        flush=True,
                    )
                    cursor_up = self._cursor_moves_to_item(self._currentindex)
                    io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)
                    page_items = self.fetchitems()
                    if self._currentindex < len(page_items):
                        self._display_item(
                            page_items[self._currentindex], highlighted=True
                        )
                    io.echo("{restorecursor}", end="", flush=True)
                    continue
                return result
            if result is True:
                io.echo("{restorecursor}", end="", flush=True)
            elif result is False:
                io.echo("{BEL}", end="", flush=True)


def init():
    io.setvar("listbox.boxcolor", "{darkgreen}")
    io.setvar("listbox.titlecolor", "{inverse}")
    io.setvar("listbox.item.normal", "{white}")
    io.setvar("listbox.item.highlighted", "{listbox.item.normal}{inverse}")
    io.setvar("listbox.item.disabled", "{darkgray}")
    io.setvar("listbox.bgcolor", "")
