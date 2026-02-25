from math import ceil
from typing import Any, Callable, List, NamedTuple, Optional

from .listbox import Listbox, ListboxItem, ListboxResult


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
            idle,
            custom_keys,
            **kwargs,
        )
        self.cur = cur
        self.totalitems = totalitems
        self.itemclass = itemclass
        self._cursor_position = 0

        self.numpages = max(1, ceil(self.totalitems / self.itemsperpage))

    def fetchitems(self) -> List[ListboxItem]:
        start = self._curpage * self.itemsperpage

        if start != self._cursor_position:
            self.cur.scroll(start - self._cursor_position, mode="relative")
            self._cursor_position = start

        rows = self.cur.fetchmany(self.itemsperpage)
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
