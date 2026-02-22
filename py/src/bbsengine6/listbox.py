from math import ceil
from typing import Any, Callable, NamedTuple, Optional

from . import io, screen


class Op(NamedTuple):
    kind: str
    listitem: Optional[Any]


class ListboxItem:
    WIDTH_OVERHEAD = 9

    status: str
    label: str
    itemid: Optional[Any]
    pk: Any
    rec: dict[str, Any]
    width: int
    height: int

    @classmethod
    def compose(cls, rec: dict[str, Any], counter: int) -> dict[str, Any]:
        return {"label": f"item #{counter}", "height": 1}

    def __init__(
        self,
        rec: dict[str, Any],
        width: int,
        height: int = 1,
        counter: int = 0,
        pk: Any = None,
        **kwargs: Any,
    ) -> None:
        composed = self.compose(rec, counter)
        self.status = ""
        self.label = composed["label"]
        self.height = max(1, composed["height"])
        self.itemid = None
        self.pk = pk if pk is not None else counter
        self.rec = rec
        self.width = width

    def help(self) -> None:
        io.echo("this is a help message in a callable")

    def display(self) -> None:
        lines = self.label.split("\n")
        for line in lines:
            padded = line.ljust(self.width - self.WIDTH_OVERHEAD, " ")
            io.echo(
                f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}} {padded} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}",
                end="",
                flush=True,
            )


class Listbox:
    args: Any
    kwargs: dict[str, Any]
    page: int
    curpos: int
    pagesize: int
    items: list[ListboxItem]
    title: str
    currentitem: Optional[ListboxItem]
    keyhandler: Optional[Callable[[Any, str, "Listbox"], Any]]
    totalitems: int
    terminalwidth: int
    itemclass: Optional[type[ListboxItem]]
    numpages: int
    numitems: int
    data: Optional[list[Any]]

    def __init__(
        self,
        args: Any,
        title: str = "",
        pagesize: int = 20,
        keyhandler: Optional[Callable[[Any, str, "Listbox"], Any]] = None,
        totalitems: int = 0,
        itemclass: Optional[type[ListboxItem]] = None,
        data: Optional[list[Any]] = None,
        **kwargs: Any,
    ) -> None:
        self.args = args
        self.kwargs = kwargs
        self.page = 0
        self.curpos = 0
        self.pagesize = pagesize
        self.items = []
        self.title = title
        self.currentitem = None
        self.keyhandler = keyhandler
        self.totalitems = totalitems
        self.terminalwidth = io.terminal.width()
        self.itemclass = itemclass
        self.data = data
        self.fetchpage()
        if self.totalitems == 0 and self.data is not None:
            self.totalitems = len(self.data)
        self.numpages = max(1, int(ceil(self.totalitems / self.pagesize)))
        self.numitems = 0

    def getpage(self, page: int, pagesize: int) -> list[ListboxItem]:
        if self.itemclass is None:
            io.echo(
                "bbsengine.listbox.Listbox.getpage: itemclass is None", level="error"
            )
            return []

        if self.data is None:
            io.echo("bbsengine.listbox.Listbox.getpage: data is None", level="error")
            return []

        start = page * pagesize
        end = start + pagesize
        page_data = self.data[start:end]

        items: list[ListboxItem] = []
        counter = start
        for rec in page_data:
            pk = rec.get("pk") if isinstance(rec, dict) else None
            items.append(
                self.itemclass(
                    rec,
                    self.terminalwidth,
                    counter=counter,
                    pk=pk,
                    **self.kwargs,
                )
            )
            counter += 1
        return items

    def fetchpage(self) -> list[ListboxItem]:
        self.items = self.getpage(self.page, self.pagesize)
        self.numitems = len(self.items)
        return self.items

    def displayitems(self) -> None:
        num = 0
        for item in self.items:
            if (
                self.currentitem is not None
                and hasattr(self.currentitem, "pk")
                and hasattr(item, "pk")
                and self.currentitem.pk == item.pk
            ):
                io.setvar("cic", "{var:currentitemcolor}")
            else:
                io.setvar("cic", "{var:itemcolor}")
            item.display()
            io.echo()
            num += 1
        if num < self.pagesize:
            for i in range(0, self.pagesize - num):
                io.echo(
                    f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}} {' '.ljust(self.terminalwidth - 8, ' ')}{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}"
                )

    def display(self) -> None:
        io.echo(f"{self.curpos=} {self.page=} {self.numitems=}", level="debug")
        self.fetchpage()
        if self.items and self.curpos < len(self.items):
            self.currentitem = self.items[self.curpos]

        io.echo(
            "{/all}{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}"
            % (" " * (self.terminalwidth - 2)),
            wordwrap=False,
        )
        if self.title is None or self.title == "":
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth - 7}}}{{var:engine.menu.boxcharcolor}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}",
                wordwrap=False,
            )
        else:
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth - 7}}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}",
                wordwrap=False,
            )
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.titlecolor}}{self.title.center(self.terminalwidth - 7)}{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}",
                wordwrap=False,
            )
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ltee}}{{acs:hline:{self.terminalwidth - 7}}}{{acs:rtee}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}",
                wordwrap=False,
            )

        if self.args.debug is True:
            screen.setbottombar(
                f"{self.curpos=} {len(self.items)=} {self.currentitem=}"
            )

        self.displayitems()

        io.echo(
            f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:llcorner}}{{acs:hline:{self.terminalwidth - 7}}}{{acs:lrcorner}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}",
            wordwrap=False,
        )
        io.echo(
            f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}}  {{var:engine.menu.shadowcolor}}{' ' * (self.terminalwidth - 6)} {{var:engine.menu.color}} {{/all}}",
            wordwrap=False,
        )
        io.echo(
            f" {{var:engine.menu.color}}{' ' * (self.terminalwidth - 2)}{{/all}}",
            wordwrap=False,
        )

    def handle(self, prompt: str = "listbox: ") -> Op | bool | None:
        io.echo(
            f"{{f6}} {prompt}{{savecursor}}{{cha}}{{cursorright:4}}{{cursorup:4}}{{cursorup:{self.pagesize - self.curpos}}}{{var:engine.menu.cursorcolor}}{{cursorleft}}",
            end="",
            flush=True,
        )
        if self.items and self.curpos < len(self.items):
            self.currentitem = self.items[self.curpos]

        done = False
        while not done:
            if not self.items:
                return Op("noitems", None)
            ch = io.getch(noneok=False)
            if ch is None:
                continue
            io.setvar("cic", "{var:itemcolor}")
            if self.currentitem is not None:
                self.currentitem.display()
            if ch == "KEY_DOWN":
                if self.curpos + 1 < self.numitems:
                    io.echo(
                        f"{{var:engine.menu.cursorcolor}}{{cursordown:{self.currentitem.height if self.currentitem else 1}}}",
                        end="",
                        flush=True,
                    )
                    self.curpos += 1
                else:
                    if self.page >= self.numpages - 1:
                        io.echo("{bell}", end="", flush=True)
                    elif (
                        self.curpos + 1 == self.numitems
                        and self.page + 1 >= self.numpages
                    ):
                        io.echo("{bell}", end="", flush=True)
                    else:
                        screen.setarea(f"{self.curpos=}")
                        io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                        self.curpos = 0
                        self.page += 1
                        self.fetchpage()
                        if self.items:
                            self.currentitem = self.items[self.curpos]
                        self.displayitems()
                        io.echo(f"{{cursorup:{self.pagesize}}}", end="", flush=True)
            elif ch == "KEY_UP":
                if self.curpos > 0:
                    io.echo(
                        f"{{cursorup:{self.currentitem.height if self.currentitem else 1}}}",
                        end="",
                        flush=True,
                    )
                    self.curpos -= 1
                else:
                    if self.curpos == 0 and self.page == 0:
                        io.echo("{bell}", end="", flush=True)
                    else:
                        io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                        self.page -= 1
                        self.fetchpage()
                        self.displayitems()
                        self.curpos = self.numitems - 1
                        if self.items:
                            self.currentitem = self.items[self.curpos]
                        io.echo("{cursorup}", end="", flush=True)
            elif ch == "KEY_HOME":
                if self.curpos > 0:
                    io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                    self.curpos = 0
            elif ch == "KEY_END":
                io.echo(
                    f"{{cursordown:{self.numitems - self.curpos - 1}}}",
                    end="",
                    flush=True,
                )
                self.curpos = self.numitems - 1
            elif ch == "?" or ch == "KEY_HELP":
                return Op("help", self.items[self.curpos - 1] if self.items else None)
            elif ch == "KEY_PAGEDOWN":
                if self.page + 1 >= self.numpages:
                    io.echo("{bell}", end="", flush=True)
                else:
                    io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                    self.page += 1
                    self.curpos = 0
                    self.fetchpage()
                    if self.items:
                        self.currentitem = self.items[self.curpos]
                    self.displayitems()
                    io.echo(f"{{cursorup:{self.pagesize}}}", end="", flush=True)
            elif ch == "KEY_PAGEUP":
                if self.page == 0:
                    io.echo("{bell}", end="", flush=True)
                else:
                    io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                    self.page -= 1
                    self.curpos = 0
                    self.fetchpage()
                    if self.items:
                        self.currentitem = self.items[self.curpos]
                    self.displayitems()
                    io.echo(f"{{cursorup:{self.numitems}}}", end="", flush=True)
            elif ch == "X":
                io.echo("{restorecursor}exit")
                return Op("exit", self.currentitem)
            elif ch == "KEY_ENTER":
                io.echo("{restorecursor}", end="")
                return Op("select", self.currentitem)
            else:
                if callable(self.keyhandler):
                    if self.keyhandler(self.args, ch, self) is False:
                        io.echo("{bell}", end="", flush=True)
                        continue
                    else:
                        return True
                else:
                    io.echo("{bell}", end="", flush=True)
                    continue

            if self.curpos >= self.numitems:
                io.echo("{bell}")
            else:
                io.setvar("cic", "{var:currentitemcolor}")
                if self.items:
                    self.currentitem = self.items[self.curpos]
                    self.currentitem.display()

            if self.args.debug is True:
                screen.setarea(
                    f"{self.curpos=} {len(self.items)=} {self.currentitem.pk if self.currentitem and hasattr(self.currentitem, 'pk') else 'N/A'}"
                )
        return Op("unknown", self.currentitem)

    def run(self, prompt: str = "listbox: ") -> Optional[Op]:
        self.items = self.fetchpage()
        self.numitems = len(self.items)

        if self.numitems == 0:
            io.echo("no list items defined.", level="error")
            return Op("noitems", None)

        self.currentitem = self.items[self.curpos]

        done = False
        while not done:
            self.display()

            res = self.handle(prompt)

            if res is None:
                io.echo("self.handle() returned None", level="debug")
                return None
            elif res is True:
                continue

            item = res.listitem

            if res.kind == "refresh":
                io.echo("{decrc}refresh")
                continue
            elif res.kind == "select":
                return Op("select", item)
            elif res.kind == "help":
                io.echo(
                    f"{{restorecursor}}{{var:labelcolor}}{item.label if item and hasattr(item, 'label') else 'Unknown'} - help{{f6}}",
                    end="",
                    flush=True,
                )
                if item is None or not hasattr(item, "help"):
                    io.echo("{bell}", end="", flush=True)
                    continue

                if callable(item.help):
                    item.help()
                elif type(item.help) is str:
                    io.echo(item.help)
                else:
                    io.echo("{f6}no help defined for this option{f6}")
                continue
            elif res.kind == "exit":
                return Op("exit", item)
            else:
                io.echo(f"unhandled: {res=}", level="debug")

        return Op("unknown", item)
