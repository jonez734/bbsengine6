from typing import NamedTuple

import ttyio6 as ttyio
from . import screen

class Op(NamedTuple):
  kind: str
  listitem: object

class ListboxItem(object):
    def __init__(self, rec:dict):
      self.status = ""
      self.pk = rec["person_key"]
      self.label = rec["person_key"]
      self.itemid = None
      self.rec = rec

    def display(self, width):
      ttyio.echo(f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}} {self.label.ljust(width-9, '-')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}", end="", flush=True)
      return

class Listbox(object):
    def __init__(self, args, cursor, title="", callback=None):
        self.cursor = cursor
        self.page = 0
        self.curpos = 0
        self.pagesize = 10
        self.items = []
        self.title  = title
        self.args = args
        self.currentitem = None
        self.callback = callback
        self.terminalwidth = ttyio.getterminalwidth()

    def fetchpage(self):
#        ttyio.echo(f"{self.page=} {self.curpos=}", level="debug")
        self.cursor.scroll(self.page*self.pagesize, mode="absolute")
        items = []
        for rec in self.cursor.fetchmany(self.pagesize):
            items.append(ListboxItem(rec))
        return items
    
    def display(self):
        self.items = self.fetchpage()

#        width = terminalwidth - 7

#        maxlen = 0
#        for i in self.fetchpage():
#              l = len(i.label)
#              if l > maxlen:
#                  maxlen = l

        ttyio.echo("{/all}{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(self.terminalwidth-2)), wordwrap=False)
        if self.title is None or self.title == "":
          ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth-7}}}{{var:engine.menu.boxcharcolor}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}", wordwrap=False)
        else:
          ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth-7}}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}", wordwrap=False)
          ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.titlecolor}}{self.title.center(self.terminalwidth-7)}{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
          ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ltee}}{{acs:hline:{self.terminalwidth-7}}}{{acs:rtee}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)

        if self.args.debug is True:
          screen.setarea(f"{self.curpos=} {len(self.items)} {self.currentitem=}")

        options = ""
        status = ""
        for item in self.fetchpage(): # items:
#          ttyio.echo(f"{item.pk=} {self.currentitem.pk=} {item.pk == self.currentitem.pk}", level="debug")
          if self.currentitem.pk == item.pk:
            ttyio.setvar("cic", "{var:currentitemcolor}")
          else:
            ttyio.setvar("cic", "{var:itemcolor}")
#          print(f"{ttyio.getvar('cic')}")
          item.display(self.terminalwidth)
          ttyio.echo()
#            x = item.label.ljust(terminalwidth-8, " ")
#            ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.ic}}{x} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}")

        ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:llcorner}}{{acs:hline:{self.terminalwidth-7}}}{{acs:lrcorner}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
        ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}}  {{var:engine.menu.shadowcolor}}{' '*(self.terminalwidth-6)} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
        ttyio.echo(f" {{var:engine.menu.color}}{' '*(self.terminalwidth-2)}{{/all}}", wordwrap=False)
        return

    def handle(self, prompt="listbox: "):#, default="X"):
#        if self.pagesize < self.numitems:
#            n = self.pagesize
#        else:
#            n = self.numitems
        ttyio.echo(f"{{f6}} {prompt}{{decsc}}{{cha}}{{cursorright:4}}{{cursorup:{self.pagesize+4}}}{{var:engine.menu.cursorcolor}}{{cursorleft}}", end="", flush=True)

        res = None
        self.curpos = 0
        self.oldpos = 0
        
#        terminalwidth = ttyio.getterminalwidth()
#        if terminalwidth > 100:
#          terminalwidth = 100

        self.currentitem = self.items[self.curpos]

        done = False
        while not done:
          ch = ttyio.getch(noneok=False).upper()
          ttyio.setvar("cic", "{var:itemcolor}")
          self.currentitem.display(self.terminalwidth)
          if ch == "KEY_DOWN":
            if self.curpos < self.pagesize-1:
#              ttyio.echo(f"{{var:engine.menu.cursorcolor}}{self.items[self.curpos].label}{{cha}}{{cursorright:3}}{{cursordown}}", end="", flush=True) # chr(ord('A')+self.pos)), end="", flush=True)
              ttyio.echo(f"{{var:engine.menu.cursorcolor}}{{cursordown}}", end="", flush=True) # chr(ord('A')+self.pos)), end="", flush=True)
              self.curpos += 1
            else:
              ttyio.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              self.curpos = 0
          elif ch == "KEY_UP":
            if self.curpos > 0:
              ttyio.echo("{cursorup}", end="", flush=True)
              self.curpos -= 1
            else:
              ttyio.echo(f"{{cursordown:{self.pagesize-1}}}", end="", flush=True)
              self.curpos = self.pagesize-1
          elif ch == "KEY_ENTER":
            ttyio.echo("{restorecursor}", end="", flush=True)
            return Op("select", self.items[self.curpos])
          elif ch == "KEY_HOME":
            if self.curpos > 0:
              ttyio.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              self.curpos = 0
          elif ch == "KEY_END":
            ttyio.echo(f"{{cursordown:{self.pagesize-self.curpos-1}}}", end="", flush=True)
            self.curpos = self.pagesize-1
          elif ch == "?" or ch == "KEY_HELP":
            return Op("help", self.items[self.curpos-1])
          elif ch == "KEY_PAGEUP":
            if self.page == 0:
              ttyio.echo(f"{{bell}}", end="", flush=True)
            else:
              ttyio.echo("page up")
          elif ch == "X":
            ttyio.echo("{restorecursor}exit")
            done = True
            break
          else:
#            ttyio.echo(f"{self.callback=}", level="debug")
            if callable(self.callback) is True:
              done = self.callback(self.args, ch, self.currentitem)
              if done is False:
                ttyio.echo("{bell}", end="", flush=True)
            else:
              ttyio.echo("{bell}", end="", flush=True)

          ttyio.setvar("cic", "{var:currentitemcolor}")
          self.currentitem = self.items[self.curpos]
          self.currentitem.display(self.terminalwidth)

          if self.args.debug is True:
            screen.setarea(f"{self.curpos=} {len(self.items)=} {self.currentmenuitem.label=}")
        return None

    def run(self, prompt="listbox: "):
        self.items = self.fetchpage()
        self.numitems = len(self.items)

        if self.numitems == 0:
          ttyio.echo("no list items defined.", level="error")
          return None

        self.currentitem = self.items[self.curpos]

        done = False
        while not done:
          self.display()
          
          res = self.handle(f"{prompt}")

          if res is None:
            ttyio.echo("self.handle() returned None", level="debug")
            return None

          item = res.listitem

          if res.kind == "refresh":
            ttyio.echo("{decrc}refresh")
            continue
          elif res.kind == "enter":
              ttyio.echo(f"{{restorecursor}}{{var:optioncolor}}{item.key}{{var:promptcolor}}: {{var:labelcolor}}{item.display(self.terminalwidth)}{{/all}}")
          elif res.kind == "help":
            ttyio.echo(f"{{restorecursor}}{{var:labelcolor}}{item.label} - help{{f6}}", end="", flush=True)
            if not hasattr(item, "help"):
              ttyio.echo("{bell}", end="", flush=True)
              continue

            if callable(item.help) is True:
              mi.help()
            elif type(item.help) is str:
              ttyio.echo(item.help)
            else:
              ttyio.echo("{f6}no help defined for this option{f6}")
            continue
          elif res.kind == "exit":
            ttyio.echo("{decrc}exiting{f6}")
            break

          return res
