import ttyio6 as ttyio

from . import module

menuitemresults = {}

class MenuItem(object):
  def __init__(self):
    self.result = None
    self.status = None
    self.description = None
    self.key = None
    self.name = None
    self.enabled = False

  def display(self):
    pass

class MenuItemCheckbox(MenuItem):
  def __init__(self):
    super().__init__()
    self.type = "CHECKBOX"

class MenuItemRadioButton(MenuItem):
  def __init__(self):
    super().__init__()
    self.type = "RADIO"
    self.value = None

class MenuItemTextbox(MenuItem):
  def __init__(self):
    super().__init__()
    self.type = "TEXT"

class Menu(object):
  def __init__(self, title:str, items, args=None, area:str=""):
    self.title = title
    self.items = items
    self.args = args
    self.area = area

  # @see https://stackoverflow.com/questions/11469025/how-to-implement-a-subscriptable-class-in-python-subscriptable-class-not-subsc
  def __getitem__(self, i:int) -> dict:
    return self.items[i]

  def __len__(self) -> int:
    return len(self.items)

  def find(self, name:str) -> bool:
    for m in self.items:
      if "name" in m and name == m["name"]:
        return m
    else:
      return None
    return False

  def resolverequires(self, menuitem) -> bool:
#    ttyio.echo("Menu.resolverequires.160: menuitem=%r" % (menuitem), interpret=False)
    if menuitem is None:
      # ttyio.echo("Menu.resolverequires.180: menuitem is None.")
      raise ValueError

    name = menuitem["name"]
    requires = menuitem["requires"] if "requires" in menuitem else ()
    if len(requires) == 0:
      # ttyio.echo("Menu.resolverequires.140: len(requires) == 0")
      return True
#    ttyio.echo("requires=%r" % (requires,), interpret=False)
    for r in requires:
      if r in menuitemresults:
#        ttyio.echo("menuitemresults[%s]=%r" % (r, menuitemresults[r]), interpet=False)
        if menuitemresults[r] is False or menuitemresults[r] is None:
#          ttyio.echo("returning False")
          return False
      else:
        return False
#    ttyio.echo("returning True")
    return True

    for r in requires:
      m = self.find(r)
      if m is None or m is False:
        return False

      if "result" in m:
        if m["result"] is False:
          return False
      else:
        return False

    return True

  def display(self):
    terminalwidth = ttyio.getterminalwidth()
    w = terminalwidth - 7

#    setarea(self.area)
#    ttyio.setvariable("engine.menu.resultfailedcolor", "{bgred}")

    maxlen = 0
    for i in self.items:
          l = len(i["label"])
          if l > maxlen:
              maxlen = l
#    ttyio.echo("menuitemresults=%r" % (menuitemresults), interpret=False)

#    ttyio.echo("{f6} {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(terminalwidth-2)), wordwrap=False)
    ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color}%s{/all}" % (" "*(terminalwidth-2)), wordwrap=False)
    if self.title is None or self.title == "":
      ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:ulcorner}{acs:hline:%d}{var:engine.menu.boxcharcolor}{acs:urcorner}{var:engine.menu.color}  {/all}" % (terminalwidth - 7), wordwrap=False)
    else:
      ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:ulcorner}{acs:hline:%d}{acs:urcorner}{var:engine.menu.color}  {/all}" % (terminalwidth - 7), wordwrap=False)
      ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.titlecolor}%s{/all}{var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % (self.title.center(terminalwidth-7)), wordwrap=False)
      ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:ltee}{acs:hline:%d}{acs:rtee}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % (terminalwidth - 7), wordwrap=False)

    ch = ord("A")
    options = ""
    status = ""
    if len(self.items) > 0:
      for i in self.items:
        result = i["result"] if "result" in i else None
        if type(result) == tuple:
          result, status = result
        elif type(result) == bool:
          status = "%r" % (result)

        if ((type(status) == tuple or type(status) == list)) and len(status) > 0:
          status = " ".join(status)
        else:
          status = "(invalid type %r)" % (type(result))

        requires = i["requires"] if "requires" in i else ()

        name = i["name"] if "name" in i else None
        if result is False:
          ttyio.setvariable("engine.menu.ic", "{var:engine.menu.resultfailedcolor}")
        else:
          if self.resolverequires(i) is True:
            ttyio.setvariable("engine.menu.ic", "{var:engine.menu.itemcolor}")
          else:
            ttyio.setvariable("engine.menu.ic", "{var:engine.menu.disableditemcolor}")

        buf = "[%s] %s" % (chr(ch), i["label"].ljust(maxlen))
        if "description" in i:
          description = i["description"]
          # descriptionlen = len(ttyio.interpretmci(description, strip=True))
          buf += " %s" % (i["description"])
        if "requires" in i and len(i["requires"]) > 0:
          buf += " (requires: %s)" % (oxfordcomma(requires))
        if "result" in i:
          result = i["result"]
          if result is True:
            buf += " PASS"
          elif result is False:
            buf += " FAIL"
#          buf += " (result: %s)" % (i["result"])

#        strippedbuf = ttyio.interpretmci(buf, strip=True)
        ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.ic}%s {/all}{var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % (buf.ljust(terminalwidth-8))) # , " "*(terminalwidth-8)), wordwrap=False)

        options += chr(ch)
        ch += 1

    ttyio.echo(" {var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.itemcolor}%s {var:engine.menu.boxcharcolor}{acs:vline}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % ("[Q] quit".ljust(terminalwidth-8)), wordwrap=False)
    options += "Q"

    ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color} {var:engine.menu.boxcharcolor}{acs:llcorner}{acs:hline:%d}{acs:lrcorner}{var:engine.menu.shadowcolor} {var:engine.menu.color} {/all}" % (terminalwidth-7), wordwrap=False)

    ttyio.echo(" {var:engine.menu.cursorcolor}{var:engine.menu.color}  {var:engine.menu.shadowcolor}%s {var:engine.menu.color} {/all}" % (" "*(terminalwidth-6)), wordwrap=False)
    ttyio.echo(" {var:engine.menu.color}%s{/all}" % (" "*(terminalwidth-2)), wordwrap=False)
    return

  def run(self, prompt="prompt: ", preprompthook=None):
    if len(self.items) == 0:
      ttyio.echo("no menu items defined.")
      return

    done = False
    while not done:
      self.display()
      if callable(preprompthook):
        preprompthook(self.args)
      res = self.handle("{var:engine.menu.promptcolor}%s{var:engine.menu.inputcolor}{decsc}" % (prompt))
      if res is None:
        return
      elif res == "KEY_FF":
        ttyio.echo("{decrc}refresh")
        continue
      elif type(res) == tuple:
        (op, i) = res
      else:
        ttyio.echo("invalid return type from handle menu %r!" % (type(res)), level="error")
        break

      if i < len(self.items):
        if op == "select":
          ttyio.echo("{decrc}{var:engine.menu.inputcolor}%s: %s{/all}" % (chr(ord('A')+i), self.items[i]["label"]))
  #        ttyio.echo("menu[i]=%r" % (menu[i]), interpret=False, level="debug", interpret=False)
          label = self.items[i]["label"]
          callback = self.items[i]["callback"]
          name = self.items[i]["name"]
          menuitem = self.items[i]
          if self.resolverequires(menuitem) is False:
            if ttyio.inputboolean("{f6}{var:promptcolor}all requirements not resolved. proceed? {var:optioncolor}[yN]{var:promptcolor}: {var:inputcolor}", "N") is False:
              continue

          res = module.runcallback(self.args, callback, menu=self, label=label) # menuitem=menuitems[i])
          if type(res) == tuple:
            if len(res) == 2:
              r, s = res
              req = None
            if type(r) is not bool:
              raise TypeError
            self.items[i]["result"] = r
            menuitemresults[name] = r
            # ttyio.echo("Menu.run.100: s=%r" % (s), level="debug")
            if type(s) == str:
              description = s
            elif (type(s) == tuple or type(s) == list) and len(s) > 0:
              description = " ".join(s)
            menuitem["description"] = description
          else:
            self.items[i]["result"] = res
            menuitemresults[name] = res
          continue
        elif op == "help":
          m = self.items[i]
          ttyio.echo("{decrc}display help for %s" % (m["label"]))
          if "help" in m:
            ttyio.echo(m["help"]+"{f6:2}")
          else:
            ttyio.echo("{f6}no help defined for this option{f6}")
          continue
      else:
        ttyio.echo("{decrc}Q: Quit{/all}")
        done = True
        break

  def handle(self, prompt="menu: ", default="Q"):
    itemcount = len(self.items)
    ttyio.echo("{f6} %s{decsc}{cha}{cursorright:4}{cursorup:%d}{var:engine.menu.cursorcolor}A{cursorleft}" % (prompt, 5+itemcount), end="", flush=True)

    res = None
    self.pos = 0
    self.oldpos = 0
    done = False
    while not done:
      ch = ttyio.getch(noneok=False)
      if ch is None:
        time.sleep(0.125)
        continue
      ch = ch.upper()
      self.oldpos = self.pos
      if ch == "Q":
        ttyio.echo("{decrc}{var:engine.menu.inputcolor}Q: Quit{/all}")
        break
      elif ch == "\004":
        raise EOFError
      elif ch == "\014": # ctrl-l (form feed)
        return "KEY_FF"
      elif ch == "KEY_DOWN":
        if self.pos < len(self.items):
          # ttyio.echo("{black}{bggray}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
          # ttyio.echo("{var:menu.cursorcolor}{var:menu.boxcolor}%s{cursorleft}{cursordown}" % (chr(ord('A')+pos)), end="", flush=True)
          ttyio.echo("{var:engine.menu.cursorcolor}%s{cursorleft}{cursordown}" % (chr(ord('A')+self.pos)), end="", flush=True)
          self.pos += 1
        else:
          ttyio.echo(f"{{cursorup:{self.pos}}}", end="", flush=True)
          self.pos = 0
      elif ch == "KEY_UP":
        if self.pos > 0:
          ttyio.echo("{cursorup}", end="", flush=True)
          self.pos -= 1
        else:
          ttyio.echo(f"{{cursordown:{len(self.items)}}}", end="", flush=True)
          self.pos = len(self.items)
      elif ch == "\n":
        # ttyio.echo("pos=%d len=%d" % (pos, len(menu)))
        return ("select", self.pos)
      elif ch == "KEY_HOME":
        if self.pos > 0:
          ttyio.echo("{cursorup:%d}" % (self.pos-1), end="", flush=True)
          self.pos = 0
      elif ch == "KEY_END":
        ttyio.echo("{cursordown:%d}" % (len(self.items)-self.pos), end="", flush=True)
        self.pos = len(self.items)+1
      elif ch == "KEY_LEFT" or ch == "KEY_RIGHT":
        ttyio.echo("{bell}", flush=True, end="")
      elif ch == "Q":
        return ("quit", None)
      elif ch == "?" or ch == "KEY_HELP":
        return ("help", self.pos)
      else:
        if len(ch) > 1:
          ttyio.echo("{bell}", end="", flush=True)
          continue
        i = ord(ch) - ord('A')
        if i > len(self.items)-1:
          ttyio.echo("{bell}", end="", flush=True)
          continue
        return ("select", i)
    return None
