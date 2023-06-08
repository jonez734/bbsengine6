import re

import ttyio6 as ttyio

from . import member
from . import database

def insert(args, sig, mogrify=False):
  attributes = sig["attributes"] if "attributes" in sig else {}
  sig["attributes"] = database.Json(attributes)

  sig["datecreated"] = "now()"
  sig["createdbyid"] = member.getcurrentid(args)
  sig["dateapproved"] = "now()"
  sig["approvedbyid"] = member.getcurrentid(args)
  return database.insert(args, "engine.__sig", sig, returnid=True, primarykey="path", mogrify=mogrify)

# @since 20210220
def update(dbh, path, sig):
  pass

class sigcompleter(object):
  def __init__(self, args):
    self.dbh = database.connect(args)
    self.matches = []

    self.debug = args.debug
    if self.debug is True:
      print ("init sigcompleter object")

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
      print (sql, dat)
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

def input(args, prompt:str="sig: ", oldvalue:str="", multiple:bool=True, verify:callable=allexist, **kw) -> str:
  if args.debug is True:
    ttyio.echo("inputsig entered. multiple=%r verify=%r" % (multiple, verify), level="debug")

  return ttyio.inputstring(prompt, oldvalue, args=args, verify=verify, multiple=multiple, completer=sigcompleter(args), returnseq=True, **kw)
