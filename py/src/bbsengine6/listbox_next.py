from math import ceil
from typing import Any, Callable, List, NamedTuple, Optional

from . import io
from .common import logentry

class ListboxItem:
    content: str
    pk: Any
    data: Any
    disabled: bool
    onkey: Optional[Callable[["ListboxItem", str], bool]] = None

    def __init__(
        self,
        content: str = "",
        pk: Any = None,
        data: Any = None,
        disabled: bool = False,
        onkey: Optional[Callable[["ListboxItem", str], bool]] = None,
        **kwargs: Any,
    ) -> None:
        self.content = content
        self.pk = pk
        self.data = data
        self.disabled = disabled
        self.onkey = onkey

    def handle_key(self, key: str) -> bool:
        return False


class ListboxResult(NamedTuple):
    status: str
    item: Optional[ListboxItem] = None
    data: Optional[dict] = None


class Listbox:
    GETCH_TIMEOUT = 0.25
    BOTTOM_BORDER_HEIGHT = 1

    itemcolors = {
        "disabled": "{bggray}",
        "highlighted": "{bgwhite}{black}",
        "normal": "{normalcolor}",
    }

    def __init__(
        self,
        args: Any,
        title: str = "",
        itemsperpage: int = 20,
        itemheight: int = 1,
        items: Optional[List[ListboxItem]] = None,
        idle: Optional[Callable[[], None]] = None,
        custom_keys: Optional[dict[str, Callable[[], Optional[ListboxResult]]]] = None,
        **kwargs: Any,
    ) -> None:
        self.args = args
        self.title = title
        self.itemsperpage = itemsperpage
        self.itemheight = itemheight
        self.items = items if items is not None else []
        self.idle = idle
        self.custom_keys = custom_keys if custom_keys else {}
        self.kwargs = kwargs

        self._curpage = 0
        self._currentindex = 0

        self.terminalwidth = io.terminal.width()
        self.contentwidth = self.terminalwidth - 3 * 2
        self.totalwidth = self.contentwidth + 6
        self.hline = f"{{hline:{self.contentwidth - 2}}}"

        self.numpages = max(1, int(ceil(len(self.items) / self.itemsperpage)))

        self.key_handlers: dict[str, Callable[[], Optional[ListboxResult]]] = {
            "KEY_ESC": self._handle_key_esc,
            "KEY_ENTER": self._handle_key_enter,
            "KEY_UP": self._handle_key_up,
            "KEY_DOWN": self._handle_key_down,
            "KEY_PAGEUP": self._handle_key_pageup,
            "KEY_PAGEDOWN": self._handle_key_pagedown,
            "KEY_HOME": self._handle_key_home,
            "KEY_END": self._handle_key_end,
        }
        if self.custom_keys:
            self.key_handlers.update(self.custom_keys)

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

    def _display_item(self, item: ListboxItem, highlighted: bool = False, end: str = "") -> None:
        if item.disabled:
            io.setvar("cic", self.itemcolors["disabled"])
        elif highlighted:
            io.setvar("cic", self.itemcolors["highlighted"])
        else:
            io.setvar("cic", self.itemcolors["normal"])

        padded = item.content.ljust(self.contentwidth - 4)
        io.echo(f"{{cha}} {{vline}} {{cic}}{padded}{{/all}} {{vline}}", end=end, flush=True)

    def _display_blank_line(self) -> None:
        io.echo(f" {{vline}} {' ' * (self.contentwidth - 4)} {{vline}}")

    def _display_title_box(self) -> None:
        io.echo(f" {{ulcorner}}{self.hline}{{urcorner}}")
        io.echo(f" {{vline}}{' ' * (self.contentwidth - 2)}{{vline}}")
        io.echo(f" {{vline}}{self.title.center(self.contentwidth - 2)}{{vline}}")
        io.echo(f" {{vline}}{' ' * (self.contentwidth - 2)}{{vline}}")

    def _display_middle_border(self) -> None:
        io.echo(f" {{rtee}}{self.hline}{{ltee}}")

    def _display_top_border(self) -> None:
        io.echo(f" {{ulcorner}}{self.hline}{{urcorner}}")

    def _display_bottom_border(self) -> None:
        io.echo(f" {{llcorner}}{self.hline}{{lrcorner}}")

    def _display(self) -> None:
        if self.title:
            self._display_title_box()
            self._display_middle_border()
        else:
            self._display_top_border()

        page_items = self.fetchitems()
        for i in range(self.itemsperpage):
            if i < len(page_items):
                self._display_item(page_items[i], highlighted=False)
            else:
                self._display_blank_line()
            io.echo()

        self._display_bottom_border()

    def _redraw_content_area(self) -> None:
        io.echo(f"{{cursorup:{self.itemsperpage + 1}}}", end="", flush=True)
        page_items = self.fetchitems()
        for i in range(self.itemsperpage):
            if i < len(page_items):
                highlighted = (i == self._currentindex)
                self._display_item(page_items[i], highlighted=highlighted)
            else:
                self._display_blank_line()
            io.echo()

    def _handle_key_esc(self) -> Optional[ListboxResult]:
        return ListboxResult("cancelled")

    def _handle_key_enter(self) -> Optional[ListboxResult]:
        if self.currentitem is not None and not self.currentitem.disabled:
            return ListboxResult("selected", self.currentitem)
        return False

    def _handle_key_up(self) -> Optional[ListboxResult]:
        page_items = self.fetchitems()
        prev_idx = self._get_prev_enabled_index(page_items, self._currentindex)
        if prev_idx != -1:
            cursor_up = self._cursor_moves_to_item(self._currentindex)
            io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)
            self._display_item(page_items[self._currentindex], highlighted=False)
            io.echo(f"{{cursorup}}", end="", flush=True)
            self._currentindex = prev_idx
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        elif self._curpage > 0:
            self._curpage -= 1
            page_items = self.fetchitems()
            last_idx = self._get_last_enabled_index(page_items)
            if last_idx != -1:
                self._currentindex = last_idx
            self._redraw_content_area()
            return True
        else:
            io.echo(f"{{BEL}}", end="", flush=True)
            return None

    def _handle_key_down(self) -> Optional[ListboxResult]:
        page_items = self.fetchitems()
        next_idx = self._get_next_enabled_index(page_items, self._currentindex)
        if next_idx != -1:
            cursor_up = self._cursor_moves_to_item(self._currentindex)
            io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)
            self._display_item(page_items[self._currentindex], highlighted=False)
            io.echo(f"{{cud}}", end="", flush=True)
            self._currentindex = next_idx
            self._display_item(page_items[self._currentindex], highlighted=True)
            return True
        elif self._curpage < self.numpages - 1:
            self._curpage += 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            self._redraw_content_area()
            return True
        else:
            io.echo(f"{{BEL}}", end="", flush=True)
            return None

    def _handle_key_pageup(self) -> Optional[ListboxResult]:
        if self._curpage > 0:
            self._curpage -= 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            self._redraw_content_area()
            return True
        else:
            io.echo(f"{{BEL}}", end="", flush=True)
            return None

    def _handle_key_pagedown(self) -> Optional[ListboxResult]:
        if self._curpage < self.numpages - 1:
            self._curpage += 1
            page_items = self.fetchitems()
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1:
                self._currentindex = first_idx
            self._redraw_content_area()
            return True
        else:
            io.echo(f"{{BEL}}", end="", flush=True)
            return None

    def _handle_key_home(self) -> Optional[ListboxResult]:
        page_items = self.fetchitems()
        first_idx = self._get_first_enabled_index(page_items)
        if first_idx != -1 and self._currentindex != first_idx:
            old_idx = self._currentindex
            cursor_up = self._cursor_moves_to_item(old_idx)
            io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)
            self._display_item(page_items[old_idx], highlighted=False)
            diff = old_idx - first_idx
            io.echo(f"{{cursorup:{diff}}}", end="", flush=True)
            self._currentindex = first_idx
            self._display_item(page_items[first_idx], highlighted=True)
        return True

    def _handle_key_end(self) -> Optional[ListboxResult]:
        page_items = self.fetchitems()
        last_idx = self._get_last_enabled_index(page_items)
        if last_idx != -1 and self._currentindex != last_idx:
            old_idx = self._currentindex
            cursor_up = self._cursor_moves_to_item(old_idx)
            io.echo(f"{{cursorup:{cursor_up}}}", end="", flush=True)
            self._display_item(page_items[old_idx], highlighted=False)
            diff = last_idx - old_idx
            io.echo(f"{{cud:{diff}}}", end="", flush=True)
            self._currentindex = last_idx
            self._display_item(page_items[last_idx], highlighted=True)
        return True

    def onkey(self, ch: Optional[str]) -> Optional[ListboxResult] | bool:
        if ch is None:
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

        if self.currentitem is not None and callable(self.currentitem.onkey):
            if self.currentitem.onkey(self.currentitem, ch):
                return True
            else:
                return False

        return False

    def _cursor_moves_to_item(self, item: int) -> int:
        return self.itemsperpage - item + 1

    def run(self, prompt: str = "listbox_next: ") -> ListboxResult:
        if not self.items:
            return ListboxResult("noitems")

        self._display()
        io.echo(f"{prompt}{{savecursor}}", end="", flush=True)

        cursor_up = self._cursor_moves_to_item(self._currentindex)
        logentry(f"{cursor_up=}", level="debug")
        io.echo(f"{{cha}}{{cursorup:{cursor_up}}}", end="", flush=True)

        page_items = self.fetchitems()
        if self._currentindex < len(page_items):
            self._display_item(page_items[self._currentindex], highlighted=True)

        io.echo(f"{{restorecursor}}", end="", flush=True)

        while True:
            result = self.onkey(io.getch(self.GETCH_TIMEOUT))
            if isinstance(result, ListboxResult):
                return result
            if result is True:
                io.echo(f"{{restorecursor}}", end="", flush=True)
            elif result is False:
                io.echo(f"{{BEL}}", end="", flush=True)
