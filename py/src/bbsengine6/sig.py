import re

import ttyio6 as ttyio

from . import member
from . import database

def builduri(args, path, top="top"):
  path = path.replace(top, "")
  path = path.lstrip(".")
  path = path.replace(".", "/")
  if path[:-1] != "/":
    return path + "/"
  else:
    return path

def builddict(args, rec):
  sig = {}
  for col in ("path", "uri", "title", "name", "intro", "attributes"):
    if col in rec:
      sig[col] = rec[col]
  return sig

def buildrec(args, sig):
  for col in ("path", "uri", "title", "name", "intro", "attributes"):
    if col in sig:
      rec[col] = sig[col]

def insert(args, sig, mogrify=False):
  attributes = sig["attributes"] if "attributes" in sig else {}
  sig["attributes"] = database.Json(attributes)

  sig["datecreated"] = "now()"
  sig["createdbyid"] = member.getcurrentid(args)
  sig["dateapproved"] = "now()"
  sig["approvedbyid"] = member.getcurrentid(args)
  return database.insert(args, "engine.__sig", sig, returnid=True, primarykey="path", mogrify=mogrify)

def get(args, path):
  sql = "select * from engine.sig where path ~ %s"
  dat = (path,)
  dbh = database.connect(args)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if args.debug is True:
    ttyio.echo(f"mogrify={cur.mogrify(sql, dat)}", level="debug")
  if cur.rowcount == 0:
    return None
  sig = cur.fetchone()
  return builddict(args, sig)

# @since 20210220
def update(args, path:str, sig:dict) -> bool:
  return database.update(args, "engine.__sig", path, sig, "path", mogrify=True)

class sigcompleter(object):
  def __init__(self, args=None):
    self.args = args
    self.dbh = database.connect(args)
    self.matches = []

    self.debug = args.debug
    if self.debug is True:
      ttyio.echo("init sigcompleter object", level="debug")

  def getmatches(self, text):
    sql = "select distinct path from engine.sig where path ~ %s"

    if text == "":
      dat = ("top.*{1}",)
    elif text[-1] == ".":
      dat = (text+"*{1}",)
    else:
      dat = (text+"*",)
    cur = self.dbh.cursor()
    if self.debug is True:
      ttyio.echo(f"mogrify={cur.mogrify(sql,dat)!r}", level="debug")
    cur.execute(sql, dat)
    res = cur.fetchall()
    foo = []
    for rec in res:
      foo.append(rec["path"])

    cur.close()
#    print foo
    return foo
  
  def complete(self, text, state):
#    print "state=",state,"text=",text
    if state == 0:
      self.matches = self.getmatches(text)
    
    return self.matches[state]

# @since 20230521 copied from bbsengine5
def buildlist(sigs:str) -> list:
#  ttyio.echo("bbsengine6.sig.buildsiglist.100: ")
  if type(sigs) == str:
    sigs = re.split("[, ]", sigs)

  sigs = [s.strip() for s in sigs]
  sigs = [s for s in sigs if s]

  return sigs

# @since 20230522 check that all sigpaths listed in buffer do not exist
def noneexist(buf, **kw):
  args = kw["args"] if "args" in kw else {}

  dbh = database.connect(args)
  cur = dbh.cursor()
  sql = "select 1 from engine.sig where path ~ %s"
  for s in buildlist(buf):
    dat = (s,)
    cur.execute(sql, dat)
    if cur.rowcount == 1:
      ttyio.echo(f"sig {s!r} already exists")
      return False
  return True

def allexist(buf, **kw):
  args = kw["args"] if "args" in kw else None

  dbh = database.connect(args)
  cur = dbh.cursor()

  sql = "select 1 from engine.sig where path ~ %s"
  for s in buildlist(buf):
    dat = (s,)
    cur.execute(sql, dat)
    if cur.rowcount == 0:
      ttyio.echo(f"sig {s!r} does not exist")
      return False

  return True

def getchsigcompleter(word, **kw):
  def build(word, **kw):
    args = kw["args"] if "args" in kw else None

    sql = "select distinct path from engine.sig where path ~ %s"

    if word == "":
      dat = ("top.*{1}",)
    elif word[-1] == ".":
      dat = (word+"*{1}",)
    else:
      dat = (word+"*",)

    dbh = database.connect(args)
    cur = dbh.cursor()
    if args.debug is True:
      ttyio.echo(f"mogrify={cur.mogrify(sql,dat)!r}", level="debug")
    cur.execute(sql, dat)
    if cur.rowcount == 0:
      return None

    for rec in database.resultiter(cur):
      yield rec["path"]
    return None

  return [x for x in build(word, **kw) if x is not None and x.startswith(word)]

def input(prompt:str="sig: ", oldvalue:str="", **kw): # multiple:bool=True, verify:callable=allexist, **kw) -> str:
  ttyio.echo(f"bbsengine6.sig.input.120: {kw=}", level="debug")
  return ttyio.inputstring(prompt, oldvalue, **kw) # args=args, verify=verify, multiple=multiple, completer=Completer, returnseq=True, **kw)
