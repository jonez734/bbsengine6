import argparse
from bbsengine6 import io, screen
from bbsengine6.listbox import Listbox, ListboxItem, ListboxResult


def buildargs():
    parser = argparse.ArgumentParser("demo_listbox_static_itemheight2")
    parser.add_argument("--debug", action="store_true", dest="debug")
    return parser


def handle_e(listbox):
    item = listbox.currentitem
    io.echo(f"{{restorecursor}}", end="", flush=True)
    io.echo(f"{{labelcolor}}Item: {{valuecolor}}{item.content}{{/all}}\n")
    io.echo(f"{{labelcolor}}pk: {{valuecolor}}{item.pk}{{/all}}\n")
    io.echo(f"{{labelcolor}}data: {{valuecolor}}{item.data}{{/all}}\n")
    io.echo(f"Press any key to continue...")
    io.getch(30)
    return ListboxResult("redraw")


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
    io.setvar("normalcolor", "{blue}{bglightgray}")
    io.setvar("cic", "{blue}{bglightgray}")
    io.setvar("labelcolor", "{yellow}")
    io.setvar("valuecolor", "{cyan}")

    prompt = "projmon: "

    screen.init()

    nato = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey", "xray", "yankee", "zulu"]

    items = []
    for i in range(28):
        nato_code = nato[i % len(nato)]
        items.append(ListboxItem(content=f"demo item #{i}\n{nato_code}", pk=i, data=None))

    def custom_e():
        return handle_e(lb)

    lb = Listbox(
        args,
        title="Demo Listbox Itemheight=3",
        itemsperpage=5,
        itemheight=2,
        items=items,
        custom_keys={"e": custom_e},
    )

    result = lb.run(prompt)

    if result is None:
        io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}listbox_next.run() returned None")
    elif result.status == "noitems":
        io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}no items")
    elif result.status == "cancelled":
#        io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}cancelled")
        io.echo(f"{{restorecursor}}cancelled")
    elif result.status == "selected" and result.item is not None:
        io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}{result.item.content} (pk={result.item.pk})")


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
            f"{{savecursor}}{{curpos:{io.terminal.height()},0}}{{eraseline}}{{reset}}{{restorecursor}}"
        )
