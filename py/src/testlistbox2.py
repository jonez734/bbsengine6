import argparse
from bbsengine6 import io, listbox


def selectresource(args, **kw):
    class EmpyreResourceListboxItem(object):
        def __init__(self, rec, width, **kw):
            self.resource = rec
            self.width = width
            self.pk = rec["pk"]
            self.labels = []
            self.labels.append(f"item {self.pk}")
            self.labels.append(f"line 2")
            self.height = len(self.labels)

        def display(self):
            # io.echo(f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}} {self.label.ljust(self.width-9, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}", end="", flush=True)
            for elle in self.labels:
                io.echo(
                    f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}}",
                    end="",
                )
                io.echo(
                    f" {elle.ljust(self.width - 9, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}",
                    end="",
                    flush=True,
                )
            return

    class EmpyreResourceListbox(listbox.Listbox):
        def __init__(self, args, **kw):
            self.player = kw["player"] if "player" in kw else None
            self.ship = kw["ship"] if "ship" in kw else None
            self.itemclass = kw["itemclass"] if "itemclass" in kw else None
            self.pagesize = 10
            self.terminalwidth = io.getterminalwidth()

            self.data = []
            for x in range(0, 30):
                rec = {}
                rec["label"] = f"item {x}"
                rec["pk"] = x
                self.data.append(
                    self.itemclass(rec, self.terminalwidth)
                )  # f"item {x}")
            self.totalitems = len(self.data)

            super().__init__(
                args,
                title="select resource",
                data=self.data,
                pagesize=self.pagesize,
                itemclass=self.itemclass,
                totalitems=self.totalitems,
            )
            io.echo(f"===> {self.totalitems=} {self.numpages=}", level="debug")

        def fetchpage(self):
            self.items = []
            for x in range(
                self.page * self.pagesize, self.pagesize + self.pagesize * self.page
            ):
                print(f"{x=}")
                self.items.append(self.data[x])
            self.numitems = len(
                self.items
            )  # number of items on the page in case it doesn't equal pagesize
            return self.items

    player = kw["player"] if "player" in kw else None
    lb = EmpyreResourceListbox(
        args, title="select resource", itemclass=EmpyreResourceListboxItem
    )  # player=kw["player"])
    res = lb.run("resource: ")
    io.echo(f"{res=}", level="debug")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("testlistbox2")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    selectresource(args)
