from math import ceil
from typing import NamedTuple

#import ttyio6 as ttyio
from . import io, screen

class Op(NamedTuple):
  kind: str
  listitem: object

class genericListboxItem(object):
    def __init__(self, rec:dict, width:int, counter=1):
      self.status = ""
#      self.pk = f"{rec['person_key']}{rec['date_start']}"
      self.label = f"item #{counter}"
      self.itemid = None
#      self.rec = rec
      self.width = width
    def help(self):
      io.echo("this is a help message in a callable")

    def display(self):
      io.echo(f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:cic}} {self.label.ljust(self.width-9, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}", end="", flush=True)
      return

class Listbox(object):
    def __init__(self, args, title="", pagesize=20, keyhandler=None, totalitems=0, itemclass=None, cur=None, **kw):
        self.cur = cur
        self.page = 0
        self.curpos = 0
        self.pagesize = pagesize
        self.items = []
        self.title  = title
        self.args = args
        self.currentitem = None
        self.keyhandler = keyhandler
        self.totalitems = totalitems
        self.terminalwidth = io.terminal.width()
        self.itemclass = itemclass
        self.fetchpage()
        self.numpages = ceil(self.totalitems / self.pagesize)
        self.numitems = 0
        io.echo(f"{self.totalitems=} {self.numpages=} {self.numitems=}", level="debug")

    def fetchpage(self):
#        ttyio.echo(f"{self.page=} {self.curpos=}", level="debug")
        self.cur.scroll(self.page*self.pagesize, mode="absolute")
        self.items = []
        for rec in self.cur.fetchmany(self.pagesize):
            self.items.append(self.itemclass(rec, self.terminalwidth))
        self.numitems = len(self.items)
        return self.items
    
    def displayitems(self):
      num = 0
      for item in self.fetchpage(): # items:
        if self.currentitem.pk == item.pk:
          io.setvar("cic", "{var:currentitemcolor}")
        else:
          io.setvar("cic", "{var:itemcolor}")
        item.display()
        io.echo()
        num += 1
      if num < self.pagesize:
        for i in range(0, self.pagesize-num):
          io.echo(f"{{/all}}{{cha}} {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}} {' '.ljust(self.terminalwidth-8, ' ')}{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}{{cha}}")

    def display(self):
        io.echo(f"{self.curpos=} {self.page=} {self.numitems=}")
        self.fetchpage()
        self.currentitem = self.items[self.curpos]

#        width = terminalwidth - 7

#        maxlen = 0
#        for i in self.fetchpage():
#              l = len(i.label)
#              if l > maxlen:
#                  maxlen = l

        io.echo("{/all}{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(self.terminalwidth-2)), wordwrap=False)
        if self.title is None or self.title == "":
          io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth-7}}}{{var:engine.menu.boxcharcolor}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}", wordwrap=False)
        else:
          io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:{self.terminalwidth-7}}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}", wordwrap=False)
          io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.titlecolor}}{self.title.center(self.terminalwidth-7)}{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
          io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ltee}}{{acs:hline:{self.terminalwidth-7}}}{{acs:rtee}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)

        if self.args.debug is True:
          screen.setarea(f"{self.curpos=} {len(self.items)} {self.currentitem=}")

        self.displayitems()

        io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:llcorner}}{{acs:hline:{self.terminalwidth-7}}}{{acs:lrcorner}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
        io.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}}  {{var:engine.menu.shadowcolor}}{' '*(self.terminalwidth-6)} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
        io.echo(f" {{var:engine.menu.color}}{' '*(self.terminalwidth-2)}{{/all}}", wordwrap=False)
        return

    def handle(self, prompt="listbox: "):#, default="X"):
        io.echo(f"{{f6}} {prompt}{{savecursor}}{{cha}}{{cursorright:4}}{{cursorup:4}}{{cursorup:{self.pagesize-self.curpos}}}{{var:engine.menu.cursorcolor}}{{cursorleft}}", end="", flush=True)
#        io.echo(f"{io.terminal.cursorpositions=}")
        self.currentitem = self.items[self.curpos]

        res = None
#        self.curpos = 0
        
#        terminalwidth = ttyio.getterminalwidth()
#        if terminalwidth > 100:
#          terminalwidth = 100

##        self.currentitem = self.items[self.curpos]

        done = False
        while not done:
#          screen.setarea(f"{self.page+1=} {self.numpages=}")
          ch = io.getch(noneok=False).upper()
          io.setvar("cic", "{var:itemcolor}")
          self.currentitem.display()
          if ch == "KEY_DOWN":
            if self.curpos+1 < self.numitems:
              io.echo(f"{{var:engine.menu.cursorcolor}}{{cursordown}}", end="", flush=True) # chr(ord('A')+self.pos)), end="", flush=True)
              self.curpos += 1
            else:
              # io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              if self.page == self.numpages:
                io.echo("{bell}", end="", flush=True)
              elif self.curpos+1 == self.numitems and self.page+1 == self.numpages:
                io.echo("{bell}", end="", flush=True)
              else:
                screen.setarea(f"{self.curpos=}")
                io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                self.curpos = 0
                self.page += 1
                self.fetchpage()
#                io.echo(f"{self.curpos=} {self.items=}")
                self.currentitem = self.items[self.curpos]
                self.displayitems()
                io.echo(f"{{cursorup:{self.pagesize}}}", end="", flush=True)
          elif ch == "KEY_UP":
            if self.curpos > 0:
              io.echo("{cursorup}", end="", flush=True)
              self.curpos -= 1
            else:
#              io.echo(f"{{cursordown:{self.numitems-1}}}", end="", flush=True)
              if self.curpos == 0 and self.page == 0:
                io.echo("{bell}", end="", flush=True)
              else:
                io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
                self.page -= 1
                self.fetchpage()
                self.displayitems()
                self.curpos = self.numitems-1
                self.currentitem = self.items[self.curpos]
                io.echo(f"{{cursorup}}", end="", flush=True)
#          elif ch == "KEY_ENTER":
#            ttyio.echo("{restorecursor}", end="", flush=True)
#            return Op("select", self.items[self.curpos])
          elif ch == "KEY_HOME":
            if self.curpos > 0:
              io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              self.curpos = 0
          elif ch == "KEY_END":
            io.echo(f"{{cursordown:{self.numitems-self.curpos-1}}}", end="", flush=True)
            self.curpos = self.numitems-1
          elif ch == "?" or ch == "KEY_HELP":
            return Op("help", self.items[self.curpos-1])
          elif ch == "KEY_PAGEDOWN":
            if self.page+1 == self.numpages:
              io.echo("{bell}", end="", flush=True)
            else:
              io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              self.page += 1
              self.curpos = 0
              self.fetchpage()
              self.currentitem = self.items[self.curpos]
              self.displayitems()
              io.echo(f"{{cursorup:{self.pagesize}}}", end="", flush=True)
          elif ch == "KEY_PAGEUP":
            if self.page == 0:
              io.echo(f"{{bell}}", end="", flush=True)
            else:
              io.echo(f"{{cursorup:{self.curpos}}}", end="", flush=True)
              self.page -= 1
              self.curpos = 0
              self.fetchpage()
              self.currentitem = self.items[self.curpos]
              self.displayitems()
              io.echo(f"{{cursorup:{self.numitems}}}", end="", flush=True)
              # ttyio.echo("page up")
          elif ch == "X":
            io.echo("{restorecursor}exit")
            return Op("exit", self.currentitem)
          elif ch == "KEY_ENTER":
            io.echo("{restorecursor}", end="")
            return Op("select", self.currentitem)
          else:
            if callable(self.keyhandler) is True:
              if self.keyhandler(self.args, ch, self) is False:
                io.echo("{bell}", end="", flush=True)
                continue
              else:
                return True
#                done = True
#                break
            else:
              io.echo("{bell}", end="", flush=True)
              continue

          if self.curpos >= self.numitems:
            io.echo("{bell}")
          else:
            io.setvar("cic", "{var:currentitemcolor}")
            self.currentitem = self.items[self.curpos]
            self.currentitem.display()

          if self.args.debug is True:
            screen.setarea(f"{self.curpos=} {len(self.items)=} {self.currentitem.pk=}")
        return Op("unknown", self.currentitem)

    def run(self, prompt="listbox: "):
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
            io.echo(f"{{restorecursor}}{{var:labelcolor}}{item.label} - help{{f6}}", end="", flush=True)
            if not hasattr(item, "help"):
              io.echo("{bell}", end="", flush=True)
              continue

            if callable(item.help) is True:
              item.help()
            elif type(item.help) is str:
              io.echo(item.help)
            else:
              io.echo("{f6}no help defined for this option{f6}")
            continue
          elif res.kind == "exit":
#            io.echo("{restorecursor}exiting{f6}")
            return Op("exit", item)
          else:
            io.echo(f"unhandled: {res=}", level="debug")

        return Op("unknown", item)
