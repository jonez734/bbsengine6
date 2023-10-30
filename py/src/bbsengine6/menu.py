from typing import NamedTuple

import ttyio6 as ttyio
import bbsengine6 as bbsengine
from . import screen
from . import module

menuitemresults = {}

class Op(NamedTuple):
  kind: str
  menuitem: object

class Item(object):
  def __init__(self, key, label, module, **kw):

    self.key = key
    self.module = module
    self.label = label

    self.result = None
    self.status = None
    self.disabled = False
    self.description = None
    self.requires = kw["requires"] if "requires" in kw else None

  def tostr(self):
    buf = "[%s] %s" % (self.key, self.label) # .ljust(maxlen))
    if type(self.description) is str and len(self.description) > 0:
      buf += " %s" % (self.description)

#    ttyio.echo(f"bbsengine6.menu.Item.100: {self.requires=}", level="debug")

    if type(self.requires) is tuple and len(self.requires) > 0:
      buf += f" (requires: {' '.join(self.requires)})" # bbsengine.util.oxfordcomma(self.requires)})"

#    ttyio.echo(f"{self.result=}", level="debug")
    if self.result is True:
      buf += " [OK]"
    elif self.result is False:
      buf += " [FAIL]"

#    ttyio.echo(f"Item.tostr.100: {self.result=} {buf=}")
    return ttyio.tostr(buf)

class Menu(object):
  def __init__(self, args, title:str, items:list, area:str="", **kw):
    self.title = title
    self.items = items
    self.args = args
    self.area = area
    self.pos = 0
    self.currentmenuitem = None

    self.items.append(Item("X", "eXit menu", None))

  # @see https://stackoverflow.com/questions/11469025/how-to-implement-a-subscriptable-class-in-python-subscriptable-class-not-subsc
  def __getitem__(self, name:str) -> dict:
    return self.items[name]

  def __len__(self) -> int:
    return len(self.items)

  def append(self, item):
    self.items.append(item)

  def find(self, name:str):
    for mi in self.items:
      if mi.module == name:
        return mi
    return None

  def resolverequires(self, item:object) -> bool:
    if item is None:
      return True

    if item.requires is None:
      return True

    if len(item.requires) == 0:
      return True

    for r in item.requires:
      mi = self.find(r) # self.items[r]
      if mi is None or mi.result is False or mi.result is None:
        return False
    return True

  def display(self):
    terminalwidth = ttyio.getterminalwidth()
    w = terminalwidth - 7

#    setarea(self.area)
#    ttyio.setvariable("engine.menu.resultfailedcolor", "{bgred}")

    maxlen = 0
    for i in self.items:
          l = len(i.label)
          if l > maxlen:
              maxlen = l
#    ttyio.echo("menuitemresults=%r" % (menuitemresults), interpret=False)

#    ttyio.echo("{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(terminalwidth-2)), wordwrap=False)
    ttyio.echo("{/all}{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(terminalwidth-2)), wordwrap=False)
    if self.title is None or self.title == "":
      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:%d}}{{var:engine.menu.boxcharcolor}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}" % (w), wordwrap=False)
    else:
      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ulcorner}}{{acs:hline:%d}}{{acs:urcorner}}{{var:engine.menu.color}}  {{/all}}" % (w), wordwrap=False)
      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.titlecolor}}%s{{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}" % (self.title.center(w)), wordwrap=False)
      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:ltee}}{{acs:hline:%d}}{{acs:rtee}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}" % (w), wordwrap=False)

    if self.args.debug is True:
      screen.setarea(f"{self.pos=} {len(self.items)} {self.currentmenuitem=}")

    options = ""
    status = ""
    for mi in self.items:
      if mi.result is False:
        ttyio.setvariable("engine.menu.ic", "{var:engine.menu.resultfailedcolor}")
      elif self.resolverequires(mi) is False:
        ttyio.setvariable("engine.menu.ic", "{var:engine.menu.disableditemcolor}")
      elif mi == self.currentmenuitem:
        print("****foo!*****")
        ttyio.setvariable("engine.menu.ic", "{yellow}")
      else:
        ttyio.setvariable("engine.menu.ic", "{var:engine.menu.itemcolor}")

      x = mi.tostr()
      ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.ic}}{x.ljust(terminalwidth-8, ' ')} {{/all}}{{var:engine.menu.boxcharcolor}}{{acs:vline}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}")

      options += mi.key # chr(ch)
#      ch += 1

#    self.items.append(Item("X", "eXit", "exit"))
#    ttyio.echo(" {var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.itemcolor}%s {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % ("e[X]it".ljust(terminalwidth-8)), wordwrap=False)
#    options += "X"

    ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}} {{var:engine.menu.boxcharcolor}}{{acs:llcorner}}{{acs:hline:{terminalwidth-7}}}{{acs:lrcorner}}{{var:engine.menu.shadowcolor}} {{var:engine.menu.color}} {{/all}}", wordwrap=False)

    ttyio.echo(f" {{var:engine.menu.cursorcolor}}{{var:engine.menu.color}}  {{var:engine.menu.shadowcolor}}{' '*(terminalwidth-6)} {{var:engine.menu.color}} {{/all}}", wordwrap=False)
    ttyio.echo(f" {{var:engine.menu.color}}{' '*(terminalwidth-2)}{{/all}}", wordwrap=False)
    return

  def handle(self, prompt="menu: ", default="X"):
    ttyio.echo(f"{{f6}} {prompt}{{decsc}}{{cha}}{{cursorright:4}}{{cursorup:{self.numitems+4}}}{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}", end="", flush=True)
##    ttyio.echo(f"{{f6}} {prompt}{{savecursor}}{{cha}}{{cursorright:4}}{{cursorup:{4+self.numitems}}}{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}", end="", flush=True)

    res = None
    self.pos = 0
    self.oldpos = 0
    done = False
    while not done:
#      self.currentmenuitem = self.items[self.pos]

      ch = ttyio.getch(noneok=False).upper()
      if ch == "KEY_DOWN":
        if self.pos < self.numitems-1:
          # ttyio.echo("{black}{bggray}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
          # ttyio.echo("{var:menu.cursorcolor}{var:menu.boxcolor}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
          ttyio.echo(f"{{var:engine.menu.cursorcolor}}{self.items[self.pos].key}{{cursorleft}}{{cursordown}}", end="", flush=True) # chr(ord('A')+self.pos)), end="", flush=True)
          self.pos += 1
        else:
          ttyio.echo(f"{{cursorup:{self.pos}}}", end="", flush=True)
          self.pos = 0
      elif ch == "KEY_UP":
        if self.pos > 0:
          ttyio.echo("{cursorup}", end="", flush=True)
          self.pos -= 1
        else:
          ttyio.echo(f"{{cursordown:{self.numitems-1}}}", end="", flush=True)
          self.pos = self.numitems-1
      elif ch == "KEY_ENTER":
        # ttyio.echo("pos=%d len=%d" % (pos, len(menu)))
        ttyio.echo("{restorecursor}", end="", flush=True)
        return Op("select", self.items[self.pos])
      elif ch == "KEY_HOME":
        if self.pos > 0:
          ttyio.echo(f"{{cursorup:{self.pos}}}", end="", flush=True)
          self.pos = 0
      elif ch == "KEY_END":
        ttyio.echo(f"{{cursordown:{self.numitems-self.pos-1}}}", end="", flush=True)
        self.pos = self.numitems-1
#      elif ch == "KEY_LEFT" or ch == "KEY_RIGHT":
#        ttyio.echo("{bell}", flush=True, end="")
      elif ch == "?" or ch == "KEY_HELP":
        return Op("help", self.items[self.pos-1])
#        return Op("help", mi)
      elif len(ch) == 1:
          for mi in self.items:
            if self.args.debug is True:
              ttyio.echo(f"{ch=} {mi.key=}", level="debug")
            if ch == mi.key:
              ttyio.echo("{restorecursor}", end="", flush=True)
              return Op("select", mi) # ("select", mi)
      else:
        ttyio.echo("{bell}", end="", flush=True)

      self.currentmenuitem = self.items[self.pos]

      if self.args.debug is True:
        screen.setarea(f"{self.pos=} {len(self.items)=} {self.currentmenuitem.label=}")
#      self.currentmi = self.items[self.pos-1]
    return None

  def run(self, prompt="prompt: ", preprompthook=None):
    self.numitems = len(self.items)

    if self.numitems == 0:
      ttyio.echo("no menu items defined.", level="error")
      return None

    done = False
    while not done:
      self.display()

      res = self.handle(f"{{var:engine.menu.promptcolor}}{prompt}{{var:engine.menu.inputcolor}}") # {{savecursor}}")

      if res is None:
        ttyio.echo("self.handle() returned None", level="debug")
        return None

      mi = res.menuitem

      if res.kind == "refresh":
        ttyio.echo("{decrc}refresh")
        continue
      elif res.kind == "enter":
          ttyio.echo(f"{{restorecursor}}{{var:optioncolor}}{res.menuitem.key}{{var:promptcolor}}: {{var:labelcolor}}{res.menuitem.label}{{/all}}")
      elif res.kind == "help":
        ttyio.echo(f"{{restorecursor}}{{var:labelcolor}}{mi.label} - help{{f6}}", end="", flush=True)
        if not hasattr(mi, "help"):
          ttyio.echo("{bell}", end="", flush=True)
          continue

        if callable(mi.help) is True:
          mi.help()
        elif type(mi.help) is str:
          ttyio.echo(mi.help)
        else:
          ttyio.echo("{f6}no help defined for this option{f6}")
        continue
      elif res.kind == "exit":
        ttyio.echo("{decrc}exiting{f6}")
        break

      if self.resolverequires(res.menuitem) is False:
        if ttyio.inputboolean("{f6}{var:labelcolor}not all requirements have been resolved. proceed? {var:optioncolor}[yN]{var:promptcolor}: {var:inputcolor}", "N") is False:
          continue

      return res
