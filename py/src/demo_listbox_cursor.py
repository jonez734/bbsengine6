import argparse

from typing import NamedTuple

from bbsengine6 import io, util, database, screen
from bbsengine6.listboxcursor import ListboxCursor
from bbsengine6.listbox import ListboxItem, ListboxResult

YUMMYHEIGHT = 166 # cm
class Height(NamedTuple):
  cm: int
  feet: float
  inches: float

def cmtofeet(cm:int) -> NamedTuple:
  inches = cm / 2.54
  feet = inches // 12
  inches -= feet*12
  return Height(cm, feet, inches)
  
class Article2PresidentListboxItem(ListboxItem):
    def __init__(self, rec: dict, width: int, height=1):
        super().__init__()
        self.status = ""
        self.pk = f"{rec['person_key']}"
        self.content = f"{rec['name_given']} {rec['name_sur']}".ljust(width - 9, ' ')
        self.data = rec
        self.width = width
        self.disabled = False

    def help(self):
        io.echo("this is a help message in a function")

    def display(self):
        io.echo(f"{{/all}}{{cha}} {{engine.menu.cursorcolor}}{{engine.menu.color}} {{engine.menu.boxcharcolor}}{{acs:vline}}{{cic}} {self.content} {{/all}}{{engine.menu.boxcharcolor}}{{acs:vline}}{{engine.menu.shadowcolor}} {{engine.menu.color}} {{/all}}{{cha}}", end="", flush=True)
        return

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("testlistbox")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "yummyjam", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    database.buildargdatabasegroup(parser, defaults)
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

parser = buildargs()

def main(args, **kw):
  prompt = "demo_listbox_database: "
  with database.connect(args) as dbh:
    with database.cursor(dbh) as cur:
      cur.execute("select count(distinct person_key) as totalitems from article2.president")
      res = cur.fetchone()
      totalitems = res["totalitems"]
      print(f"{totalitems=}")

    sql = "select distinct person_key, name_given, name_sur, name_common from article2.president"
    with database.cursor(dbh, scrollable=True, name="presidentlistbox") as cur:
      cur.execute(sql)
      if cur.rowcount == 0:
        io.echo("no presidents")
        return None
      screen.init(args)

      custom_keys = {
        "KEY_INS": lambda: (io.echo("insert new record!"), True)[1],
        "E": lambda: (io.echo(f"edit record: {lb.currentitem.pk}"), True)[1],
        "KEY_ENTER": lambda: ListboxResult("selected", lb.currentitem) if lb.currentitem else False,
      }

      lb = ListboxCursor(
          args,
          "presidents",
          itemsperpage=20,
          itemheight=1,
          cur=cur,
          totalitems=totalitems,
          itemclass=Article2PresidentListboxItem,
          custom_keys=custom_keys,
      )
      done = False
      while not done:
        op = lb.run(prompt)
        #    io.echo(f"{op=}", level="debug")
        if op.status == "cancelled":
          io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}cancelled")
          done = True
        elif op.status == "exit":
          io.echo(f"{{inputcolor}}exit")
          return True
        elif op.status == "selected":
          io.echo(f"selected item {op.item.pk}{{f6:3}}")
          sql = f"select * from article2.person where person_key=%s"
          dat = (op.item.pk,)
          with database.cursor(dbh) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
              io.echo("there are no presidents in the database")
              return False

            person = cur.fetchone()

            util.heading("person")
            io.echo(f"{{labelcolor}}Name: {{valuecolor}}{person['name_common']} {person['name_sur']}")
            date_born = person["date_born"]
            place_born = person["place_born"] if person["place_born"] is not None else ""
            state_born = person["state_born"] if person["state_born"] is not None else ""

            date_die = person["date_die"] if person["date_die"] != "9999-99-99" else "--"
            state_die = person["state_die"] if person["state_die"] != "9999-99-99" else ""
            place_die = person["place_die"] if person["place_die"] is not None else ""

            io.echo(f"{{labelcolor}}Born: {{valuecolor}}{date_born} {place_born} {state_born}")
            io.echo(f"{{labelcolor}}Died: {{valuecolor}}{date_die} {place_die} {state_die}")
            #        io.echo(f"{{var:labelcolor}}Party: {{var:valuecolor}}{rec['party']}")
            
            sql = "select max(height) as tallest, min(height) as shortest from article2.trait, article2.president where article2.trait.person_key = article2.president.person_key"
            cur.execute(sql)
            if cur.rowcount == 0:
              tallest = None
              shortest = None
            else:
              res = cur.fetchone()
              tallest = res["tallest"]
              shortest = res["shortest"]
              #        io.echo(f"{tallest=} {shortest=}")
            
            sql = "select * from article2.trait where person_key=%s"
            dat = (op.item.pk,)
            cur.execute(sql, dat)
            if cur.rowcount > 0:
              util.heading("traits")
              trait = cur.fetchone()
              cm = trait["height"]
              height = cmtofeet(cm)
              yummyheight = cmtofeet(YUMMYHEIGHT)
              if cm == shortest:
                io.echo(f"{{labelcolor}}Height: {{valuecolor}}{height.cm}cm ({height.feet:2.0f}ft {height.inches:3.2f}in) {{reverse}}shortest{{/reverse}}")
              elif cm == tallest:
                io.echo(f"{{labelcolor}}Height: {{valuecolor}}{cm}cm ({height.feet:2.0f}ft {height.inches:3.2f}in) {{reverse}}tallest{{/reverse}}")
              else:
                io.echo(f"{{labelcolor}}Height: {{valuecolor}}{cm}cm ({height.feet:2.0f}ft {height.inches:3.2f}in)")
              
              if cm == YUMMYHEIGHT:
                io.echo("{{valuecolor}}Same{{labelcolor}} height as Yummy")
              elif cm < YUMMYHEIGHT:
                io.echo("{{valuecolor}}Shorter{{labelcolor}} than Yummy")
              elif cm > YUMMYHEIGHT:
                d1 = height.cm - yummyheight.cm
                d2 = cmtofeet(d1)
                
                io.echo(f"{{valuecolor}}Taller{{labelcolor}} than Yummy by {{valuecolor}}{d1}cm {{labelcolor}}({{valuecolor}}", end="")
                if d2.feet > 0:
                  io.echo(f"{d2.feet}ft", end="")
                io.echo(f"{d2.inches:2.3f}in{{labelcolor}})")
                #        io.echo(f"{{var:labelcolor}}{util.pluralize

            util.heading("inauguration")
            sql = "select date_start, party from article2.president where person_key = %s"
            dat = (op.item.pk,)
            cur = database.cursor(dbh)
            cur.execute(sql, dat)
            if cur.rowcount < 1:
              io.echo("** error **")
            res = cur.fetchall()
            for rec in res:
              io.echo(f"{{valuecolor}}{rec['date_start']}", end="")
              if rec["party"] != "":
                io.echo(f"{{labelcolor}} ({{valuecolor}}{rec['party']}{{labelcolor}})")
              else:
                io.echo()

            io.echo("{{promptcolor}}press any key to continue: {{inputcolor}}", end="", flush=True)
            io.getch()

            io.echo(f"enter on {op.item.pk=}", level="debug")

if __name__ == "__main__":
    init()

    args = parser.parse_args()

    try:
      main(args)
    except KeyboardInterrupt:
      io.echo("{/all}{restorecursor}*INTR*")
    except EOFError:
      io.echo("{/all}{restorecursor}*EOF*")
    finally:
      io.echo(f"{{savecursor}}{{curpos:{io.terminal.height()},0}}{{/all}}{{eraseline}}{{restorecursor}}{{reset}}")

#    io.echo(f"{io.terminal.cursorpositions=}", level="debug")
