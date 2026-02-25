from math import ceil
from typing import Any, Callable, List, Optional

from .listbox import Listbox, ListboxItem, ListboxResult
from . import io


class ListboxCursor(Listbox):
    def __init__(
        self,
        args: Any,
        title: str = "",
        itemsperpage: int = 20,
        itemheight: int = 1,
        cur: Any = None,
        totalitems: int = 0,
        itemclass: Optional[type] = None,
        idle: Optional[Callable[[], None]] = None,
        custom_keys: Optional[dict[str, Callable[[], Optional[ListboxResult]]]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            args,
            title,
            itemsperpage,
            itemheight,
            items=[],
            idle=idle,
            custom_keys=custom_keys,
            **kwargs,
        )
        self.cur = cur
        self.totalitems = totalitems
        self.itemclass = itemclass
        self._cursor_position = 0
        self._lazy_load = True

        self.numpages = max(1, ceil(self.totalitems / self.itemsperpage))

    def fetchitems(self) -> List[ListboxItem]:
        start = self._curpage * self.itemsperpage
        if getattr(self.args, 'debug', False):
            io.echo(f"fetchitems: start={start} _cursor_position={self._cursor_position}", level="debug")

        if start != self._cursor_position:
            if getattr(self.args, 'debug', False):
                io.echo(f"fetchitems: scrolling to {start}", level="debug")
            self.cur.scroll(start - self._cursor_position, mode="relative")
            self._cursor_position = start

        if getattr(self.args, 'debug', False):
            io.echo(f"fetchitems: about to fetchmany", level="debug")
        rows = self.cur.fetchmany(self.itemsperpage)
        if getattr(self.args, 'debug', False):
            io.echo(f"fetchitems: got {len(rows)} rows", level="debug")
        self._cursor_position += len(rows)

        items = []
        for row in rows:
            if self.itemclass:
                item = self.itemclass(row, self.contentwidth)
            else:
                content = str(row)
                item = ListboxItem(content=content)
            items.append(item)

        return items
