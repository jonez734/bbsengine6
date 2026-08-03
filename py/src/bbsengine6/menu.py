from typing import NamedTuple

from . import screen, io

menuitemresults = {}


class Op(NamedTuple):
    kind: str
    menuitem: object


class Item(object):
    def __init__(self, key, label, modulename, **kw):

        self.key = key
        self.module = modulename
        self.label = label

        self.result = None
        self.status = None
        self.disabled = False
        self.description = None
        self.requires = kw["requires"] if "requires" in kw else None
        self.width = io.getterminalwidth()
        if self.width > 100:
            self.width = 100

    def display(self):
        buf = f"[{self.key}] {self.label}"
        if type(self.description) is str and len(self.description) > 0:
            buf += " %s" % (self.description)

        if type(self.requires) is tuple and len(self.requires) > 0:
            buf += f" (requires: {' '.join(self.requires)})"  # bbsengine.util.oxfordcomma(self.requires)})"

        if self.result is True:
            buf += " [OK]"
        elif self.result is False:
            buf += " [FAIL]"

        io.echo(
            f"{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}}{buf.ljust(self.width - 8, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}",
            end="",
            flush=True,
        )


class Menu(object):
    def __init__(
        self, args, title: str, items: list, area: str = "", pagesize=20, **kw
    ):
        self.title = title
        self.items = items
        self.args = args
        self.area = area
        self.pos = 0
        self.currentitem = None
        self.pagesize = pagesize
        self.currentpage = 0

        self.items.append(Item("X", "eXit menu", None))

    # @see https://stackoverflow.com/questions/11469025/how-to-implement-a-subscriptable-class-in-python-subscriptable-class-not-subsc
    def __getitem__(self, name: str) -> object:
        return self.items[name]

    def __len__(self) -> int:
        return len(self.items)

    def append(self, item):
        self.items.append(item)

    def find(self, name: str):
        for mi in self.items:
            if mi.module == name:
                return mi
        return None

    def resolverequires(self, item: object) -> bool:
        if item is None:
            return True

        if item.requires is None:
            return True

        if len(item.requires) == 0:
            return True

        for r in item.requires:
            mi = self.find(r)  # self.items[r]
            if mi is None or mi.result is False or mi.result is None:
                return False
        return True

    def display(self):
        terminalwidth = io.getterminalwidth()
        if terminalwidth > 100:
            terminalwidth = 100
        w = terminalwidth - 7

        #    setarea(self.area)
        #    ttyio.setvariable("engine.menu.resultfailedcolor", "{bgred}")

        maxlen = 0
        for i in self.items:
            label_len = len(i.label)
            if label_len > maxlen:
                maxlen = label_len

        io.echo(
            "{/all}{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}"
            % (" " * (terminalwidth - 2)),
            wordwrap=False,
        )
        if self.title is None or self.title == "":
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:%d}}{{var:engine.menu.boxcharcolor}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}"
                % (w),
                wordwrap=False,
            )
        else:
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:%d}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}"
                % (w),
                wordwrap=False,
            )
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.titlecolor}}%s{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}"
                % (self.title.center(w)),
                wordwrap=False,
            )
            io.echo(
                f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ltee}}{{acs:hline:%d}}{{acs:rtee}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}"
                % (w),
                wordwrap=False,
            )

        if self.args.debug is True:
            screen.setarea(f"{self.pos=} {len(self.items)} {self.currentitem=}")

        options = ""
        num = 0
        for item in self.items:
            if item.result is False:
                io.setvar("cic", "{var:engine.menu.resultfailedcolor}")
            elif self.resolverequires(item) is False:
                io.setvar("cic", "{var:engine.menu.disableditemcolor}")
            elif self.currentitem.key == item.key:
                io.setvar("cic", "{var:currentitemcolor}")
            else:
                io.setvar("cic", "{var:itemcolor}")

            num += 1
            #      x = mi.tostr().ljust(terminalwidth-8, " ")
            #      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.ic}}{x} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}")

            item.display()
            io.echo()

            options += item.key  # chr(ch)
            if num >= self.pagesize:
                break
        #      ch += 1

        #    self.items.append(Item("X", "eXit", "exit"))
        #    ttyio.echo(" {var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.itemcolor}%s {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % ("e[X]it".ljust(terminalwidth-8)), wordwrap=False)
        #    options += "X"

        io.echo(
            f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:llcorner}}{{acs:hline:{terminalwidth - 7}}}{{acs:lrcorner}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}",
            wordwrap=False,
        )

        io.echo(
            f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}}  {{var:engine.menu.shadowcolor}}{' ' * (terminalwidth - 6)} {{var:engine.menu.color}} {{/all}}",
            wordwrap=False,
        )
        io.echo(
            f" {{var:engine.menu.color}}{' ' * (terminalwidth - 2)}{{/all}}",
            wordwrap=False,
        )
        return

    def handle(self, prompt="menu: "):  # , default="X"):
        n = self.pagesize if self.pagesize < self.numitems else self.numitems
        #      n = self.pagesize
        #    else:
        #      n = self.numitems
        io.echo(
            f"{{f6}} {prompt}{{decsc}}{{cha}}{{cursorright:4}}{{cursorup:{n - self.pos + 4}}}{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}",
            end="",
            flush=True,
        )
        ##    ttyio.echo(f"{{f6}} {prompt}{{savecursor}}{{cha}}{{cursorright:4}}{{cursorup:{4+self.numitems}}}{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}", end="", flush=True)

        self.pos = 0
        self.oldpos = 0

        self.currentitem = self.items[self.pos]

        done = False
        while not done:
            #      self.currentmenuitem = self.items[self.pos]

            ch = io.getch(noneok=False)
            if ch is None:
                io.echo("{bell}", end="", flush=True)
                continue
            ch = ch.upper()
            io.setvar("cic", "{var:itemcolor}")
            self.currentitem.display()

            if ch == "KEY_DOWN":
                if self.pos < self.numitems - 1:
                    # ttyio.echo("{black}{bggray}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
                    # ttyio.echo("{var:menu.cursorcolor}{var:menu.boxcolor}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
                    #          ttyio.echo(f"{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}{{cursordown}}", end="", flush=True) # chr(ord('A')+self.pos)), end="", flush=True)
                    io.echo(
                        f"{{var:engine.menu.cursorcolor}}{{cursordown}}",
                        end="",
                        flush=True,
                    )  # chr(ord('A')+self.pos)), end="", flush=True)

                    self.pos += 1
                else:
                    io.echo(f"{{cursorup:{self.pos}}}", end="", flush=True)
                    self.pos = 0
            elif ch == "KEY_UP":
                if self.pos > 0:
                    io.echo("{cursorup}", end="", flush=True)
                    self.pos -= 1
                else:
                    io.echo(f"{{cursordown:{self.numitems - 1}}}", end="", flush=True)
                    self.pos = self.numitems - 1
            elif ch == "KEY_ENTER":
                # ttyio.echo("pos=%d len=%d" % (pos, len(menu)))
                io.echo("{restorecursor}", end="", flush=True)
                return Op("select", self.items[self.pos])
            elif ch == "KEY_HOME":
                if self.pos > 0:
                    io.echo(f"{{cursorup:{self.pos}}}", end="", flush=True)
                    self.pos = 0
            elif ch == "KEY_END":
                io.echo(
                    f"{{cursordown:{self.numitems - self.pos - 1}}}", end="", flush=True
                )
                self.pos = self.numitems - 1
            #      elif ch == "KEY_LEFT" or ch == "KEY_RIGHT":
            #        ttyio.echo("{bell}", flush=True, end="")
            elif ch == "?" or ch == "KEY_HELP":
                help_index = max(0, self.pos - 1)
                return Op("help", self.items[help_index])
            #        return Op("help", mi)
            elif len(ch) == 1:
                for mi in self.items:
                    if self.args.debug is True:
                        io.echo(f"{ch=} {mi.key=}", level="debug")
                    if ch == mi.key:
                        io.echo("{restorecursor}", end="", flush=True)
                        return Op("select", mi)  # ("select", mi)
            else:
                io.echo("{bell}", end="", flush=True)
                continue

            io.setvar("cic", "{var:currentitemcolor}")
            self.currentitem = self.items[self.pos]
            self.currentitem.display()
            #      ttyio.echo()

            if self.args.debug is True:
                screen.setarea(
                    f"{self.pos=} {len(self.items)=} {self.currentitem.label=}"
                )
        #      self.currentmi = self.items[self.pos-1]
        return None

    def run(self, prompt="prompt: ", preprompthook=None):
        self.numitems = len(self.items)

        if self.numitems == 0:
            io.echo("no menu items defined.", level="error")
            return None

        self.currentitem = self.items[self.pos]

        done = False
        while not done:
            self.display()

            res = self.handle(
                f"{{var:engine.menu.promptcolor}}{prompt}{{var:engine.menu.inputcolor}}"
            )  # {{savecursor}}")

            if res is None:
                io.echo("self.handle() returned None", level="debug")
                return None

            mi = res.menuitem

            if res.kind == "refresh":
                io.echo("{decrc}refresh")
                continue
            elif res.kind == "enter":
                io.echo(
                    f"{{restorecursor}}{{var:optioncolor}}{res.menuitem.key}{{var:promptcolor}}: {{var:labelcolor}}{res.menuitem.label}{{/all}}"
                )
            elif res.kind == "help":
                io.echo(
                    f"{{restorecursor}}{{var:labelcolor}}{mi.label} - help{{f6}}",
                    end="",
                    flush=True,
                )
                if not hasattr(mi, "help"):
                    io.echo("{bell}", end="", flush=True)
                    continue

                if callable(mi.help) is True:
                    mi.help()
                elif type(mi.help) is str:
                    io.echo(mi.help)
                else:
                    io.echo("{f6}no help defined for this option{f6}")
                continue
            elif res.kind == "exit":
                io.echo("{decrc}exiting{f6}")
                break

            if self.resolverequires(res.menuitem) is False:
                if (
                    io.inputboolean(
                        "{f6}{var:labelcolor}not all requirements have been resolved. proceed? {var:optioncolor}[yN]{var:promptcolor}: {var:inputcolor}",
                        "N",
                    )
                    is False
                ):
                    continue

            return res
