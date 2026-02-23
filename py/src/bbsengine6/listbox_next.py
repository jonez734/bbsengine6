from math import ceil
from typing import Any, Callable, List, NamedTuple, Optional

from . import io


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


class Listbox:
    GETCH_TIMEOUT = 0.25

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
        **kwargs: Any,
    ) -> None:
        self.args = args
        self.title = title
        self.itemsperpage = itemsperpage
        self.itemheight = itemheight
        self.items = items if items is not None else []
        self.idle = idle
        self.kwargs = kwargs

        self._curpage = 0
        self._currentindex = 0

        self.terminalwidth = io.terminal.width()
        self.contentwidth = self.terminalwidth - 3 * 2
        self.totalwidth = self.contentwidth + 6
        self.hline = f"{{hline:{self.contentwidth - 2}}}"

        self.numpages = max(1, int(ceil(len(self.items) / self.itemsperpage)))

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
        if item.disabled:
            io.setvar("cic", self.itemcolors["disabled"])
        elif highlighted:
            io.setvar("cic", self.itemcolors["highlighted"])
        else:
            io.setvar("cic", self.itemcolors["normal"])

        padded = item.content.ljust(self.contentwidth - 3)
        io.echo(f" {{vline}}{padded} {{vline}}")

    def _display_blank_line(self) -> None:
        io.echo(f" {{vline}}{' ' * (self.contentwidth - 3)}{{vline}}")

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
                self._display_item(page_items[i], highlighted=(i == self._currentindex))
            else:
                self._display_blank_line()

        self._display_bottom_border()

    def onkey(self, ch: Optional[str]) -> Optional[ListboxResult]:
        if ch is None:
            if self.idle is not None and callable(self.idle):
                self.idle()
            return None

        page_items = self.fetchitems()

        if ch == "KEY_ESC":
            return ListboxResult("cancelled")

        if ch == "KEY_ENTER":
            if self.currentitem is not None and not self.currentitem.disabled:
                io.echo("{restorecursor}", end="", flush=True)
                return ListboxResult("selected", self.currentitem)
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        if ch == "KEY_UP":
            prev_idx = self._get_prev_enabled_index(page_items, self._currentindex)
            if prev_idx != -1:
                self._display_item(page_items[self._currentindex], highlighted=False)
                self._currentindex = prev_idx
                self._display_item(page_items[self._currentindex], highlighted=True)
                return None
            elif self._curpage > 0:
                self._curpage -= 1
                page_items = self.fetchitems()
                last_idx = self._get_last_enabled_index(page_items)
                if last_idx != -1:
                    self._currentindex = last_idx
                self._display()
                return None
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        if ch == "KEY_DOWN":
            next_idx = self._get_next_enabled_index(page_items, self._currentindex)
            if next_idx != -1:
                self._display_item(page_items[self._currentindex], highlighted=False)
                self._currentindex = next_idx
                self._display_item(page_items[self._currentindex], highlighted=True)
                return None
            elif self._curpage < self.numpages - 1:
                self._curpage += 1
                page_items = self.fetchitems()
                first_idx = self._get_first_enabled_index(page_items)
                if first_idx != -1:
                    self._currentindex = first_idx
                self._display()
                return None
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        if ch == "KEY_PAGEUP":
            if self._curpage > 0:
                self._curpage -= 1
                page_items = self.fetchitems()
                first_idx = self._get_first_enabled_index(page_items)
                if first_idx != -1:
                    self._currentindex = first_idx
                self._display()
                return None
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        if ch == "KEY_PAGEDOWN":
            if self._curpage < self.numpages - 1:
                self._curpage += 1
                page_items = self.fetchitems()
                first_idx = self._get_first_enabled_index(page_items)
                if first_idx != -1:
                    self._currentindex = first_idx
                self._display()
                return None
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        if ch == "KEY_HOME":
            first_idx = self._get_first_enabled_index(page_items)
            if first_idx != -1 and self._currentindex != first_idx:
                self._display_item(page_items[self._currentindex], highlighted=False)
                self._currentindex = first_idx
                self._display_item(page_items[self._currentindex], highlighted=True)
            return None

        if ch == "KEY_END":
            last_idx = self._get_last_enabled_index(page_items)
            if last_idx != -1 and self._currentindex != last_idx:
                self._display_item(page_items[self._currentindex], highlighted=False)
                self._currentindex = last_idx
                self._display_item(page_items[self._currentindex], highlighted=True)
            return None

        if self.currentitem is not None and self.currentitem.onkey is not None:
            if self.currentitem.onkey(self.currentitem, ch):
                return None
            else:
                io.echo("{BEL}", end="", flush=True)
                return None

        io.echo("{BEL}", end="", flush=True)
        return None

    def run(self, prompt: str = "listbox_next: ") -> ListboxResult:
        if not self.items:
            return ListboxResult("noitems")

        self._display()
        io.echo(prompt)
        io.echo("{savecursor}")

        while True:
            result = self.onkey(io.getch(self.GETCH_TIMEOUT))
            if result is not None:
                return result
