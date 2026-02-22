import argparse
from bbsengine6 import io, listbox


class DemoListboxItem(listbox.ListboxItem):
    @classmethod
    def compose(cls, rec: dict, counter: int) -> dict:
        name = rec.get("name", f"Item {counter}")
        height = rec.get("height", 1)
        return {"label": name, "height": height}

    def __init__(
        self,
        rec: dict,
        width: int,
        height: int = 1,
        counter: int = 0,
        pk=None,
        **kwargs,
    ):
        super().__init__(rec, width, height, counter, pk, **kwargs)
        self.pk = rec.get("id", pk)

    def help(self) -> None:
        io.echo(f"Help for {self.label}: This is item #{self.pk}")


def buildargs():
    parser = argparse.ArgumentParser("testlistboxstatic")
    parser.add_argument("--debug", action="store_true", dest="debug")
    return parser


def main(args):
    io.setvar("engine.menu.boxcharcolor", "{bglightgray}{darkgreen}")
    io.setvar("engine.menu.color", "{bggray}")
    io.setvar("engine.menu.shadowcolor", "{bgdarkgray}")
    io.setvar("engine.menu.cursorcolor", "{bglightgray}{blue}")
    io.setvar("engine.menu.boxcolor", "{bgblue}{green}")
    io.setvar("engine.menu.titlecolor", "{black}{bglightgray}")
    io.setvar("engine.menu.disableditemcolor", "{darkgray}")
    io.setvar("engine.menu.resultfailedcolor", "{bgred}{white}")

    io.setvar("itemcolor", "{blue}{bglightgray}")
    io.setvar("currentitemcolor", "{bgwhite}{black}")

    data = []
    for i in range(1, 21):
        data.append({"id": i, "name": f"Item {i:02d}"})

    lb = listbox.Listbox(
        args,
        title="Static List Demo",
        pagesize=6,
        itemclass=DemoListboxItem,
        data=data,
    )

    op = lb.run()

    if op is None:
        io.echo("listbox.run() returned None", level="debug")
    elif op.kind == "exit":
        io.echo("{inputcolor}exit")
    elif op.kind == "select":
        io.echo(f"selected: {op.listitem.label} (pk={op.listitem.pk})")
    elif op.kind == "noitems":
        io.echo("no items")


if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        io.echo("{/all}{restorecursor}*INTR*")
    except EOFError:
        io.echo("{/all}{restorecursor}*EOF*")
    finally:
        io.echo(
            f"{{savecursor}}{{curpos:{io.terminal.height()},0}}{{/all}}{{eraseline}}{{restorecursor}}{{reset}}"
        )
