import sys
import argparse

#import ttyio6 as ttyio
import bbsengine6 as bbsengine
from bbsengine6 import io
from bbsengine6 import util

class Article2PresidentListboxItem(object):
    def __init__(self, rec:dict, width:int):
      self.status = ""
      self.pk = f"{rec['person_key']}{rec['date_start']}"
      self.label = f"{rec['name_given']} {rec['name_sur']} {rec['date_start']}"
      self.itemid = None
      self.rec = rec
      self.width = width
    def help(self):
      io.echo("this is a help message in a function")

    def display(self):
      io.echo(f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}} {self.label.ljust(self.width-9, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}", end="", flush=True)
      return

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("testlistbox")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "yummyjam", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    bbsengine.database.buildargdatabasegroup(parser, defaults)
    return parser
    
def init():
    io.setvar("engine.menu.boxcharcolor", "{bglightgray}{darkgreen}")
    io.setvar("engine.menu.color", "{bggray}")
    io.setvar("engine.menu.shadowcolor", "{bgdarkgray}")
    io.setvar("engine.menu.cursorcolor", "{bglightgray}{blue}")
    io.setvar("engine.menu.boxcolor", "{bgblue}{green}")
    io.setvar("engine.menu.titlecolor", "{black}{bglightgray}")
#    ttyio.setvariable("engine.menu.promptcolor", "")
#    ttyio.setvariable("engine.menu.inputcolor", "{white}")
    io.setvar("engine.menu.disableditemcolor", "{darkgray}")
    io.setvar("engine.menu.resultfailedcolor", "{bgred}{white}")
    
    io.setvar("itemcolor", "{blue}{bglightgray}")
    io.setvar("currentitemcolor", "{bgwhite}{black}")

def keyhandler(args, ch, listbox):
    if ch in ("KEY_INS", "E", "KEY_ENTER"):
        io.setvar("cic", "{var:currentitemcolor}")
        listbox.currentitem.display()
        io.echo("{restorecursor}", end="", flush=True)

    if ch == "KEY_INS":
        io.echo("insert new record!")
        return True # key has been handled
    elif ch == "E":
        io.echo(f"edit record: {listbox.currentitem.pk}")
        return True
    elif ch == "KEY_ENTER":
        io.echo(f"selected item {listbox.currentitem.pk}{{f6:3}}")
        util.heading("info")
        io.echo("press any key to continue: ", end="", flush=True)
        io.getch()
        return True
    return False

parser = buildargs()

if __name__ == "__main__":
    init()

    args = parser.parse_args()

    dbh = bbsengine.database.connect(args)

    cur = dbh.cursor()
    cur.execute("select count(person_key) as totalitems from article2.president")
    res = cur.fetchone()
    totalitems = res["totalitems"]

    sql = "select person_key, name_sur, name_given, date_start from article2.president"
    dat = ()
    cur = dbh.cursor(scrollable=True, name="presidentlistbox")
    cur.execute(sql)
    if cur.rowcount == 0:
        io.echo("no presidents")

    bbsengine.screen.init(args)

    try:
        listbox = bbsengine.listbox.Listbox(args, cur, "presidents", callback=handlekeypress, itemclass=Article2PresidentListboxItem, totalitems=totalitems)
        op = listbox.run()
        if op is None:
            io.echo("listbox.run() returned None", level="debug")
#        elif op.kind == "select":
#            ttyio.setvar("cic", "{var:currentitemcolor}")
#            listboxitem.display(listbox.terminalwidth)
#            ttyio.echo(f"{{restorecursor}}{{var:inputcolor}}selected option {op.listitem=}")
        elif op.kind == "exit":
            io.echo(f"{{restorecursor}}{{var:inputcolor}}exit")
    #    elif op.kind == "enter":
    #        ttyio.echo(f"enter on {op.menuitem.key=}", level="debug")
    except KeyboardInterrupt:
        io.echo("{/all}{restorecursor}*INTR*")
    except EOFError:
        io.echo("{/all}{restorecursor}*EOF*")
    finally:
#        pass
        io.echo(f"{{savecursor}}{{curpos:{io.getterminalheight()},0}}{{/all}}{{eraseline}}{{restorecursor}}{{reset}}")

    io.echo(f"{io.terminal.cursorpositions=}", level="debug")

