import argparse

import ttyio6 as ttyio
import bbsengine6 as bbsengine
import bbsengine6.database as database

class Completer(object):
    def __init__(self, args, **kw):
      self.args = kw["args"]
#      self.args = kw["args"] if "args" in kw else "ARGS!"
      ttyio.echo(f"Completer.init.100: {kw=}", level="debug")
      self.debug = True

    def build(self, word):
      sql = "select distinct path from engine.sig where path ~ %s"

      if text == "":
        dat = ("top.*{1}",)
      elif text[-1] == ".":
        dat = (text+"*{1}",)
      else:
        dat = (text+"*",)
        
      dbh = database.connect(self.args)
      cur = dbh.cursor()
      if self.debug is True:
        ttyio.echo(f"mogrify={cur.mogrify(sql,dat)!r}", level="debug")
      cur.execute(sql, dat)
      if cur.rowcount == 0:
        return None

      for rec in database.resultiter(cur):
        yield rec["path"]
      return None
    
    def complete(self, word, state):
        self.results = [x for x in self.build(word) if x is not None and x.startswith(word)]
        ttyio.echo(f"self.results={self.results!r} state={state!r}", level="debug")
        return self.results

  
parser = argparse.ArgumentParser("test sig completer")
parser.add_argument("--debug", action="store_true", dest="debug", default=True)
parser.add_argument("--databasename", dest="databasename", default="zoid6")
parser.add_argument("--databasehost", dest="databasehost", default="localhost")
parser.add_argument("--databaseuser", dest="databaseuser")

args = parser.parse_args()
res = bbsengine.sig.input("prompt here: ", style="ttyio", multiple=False, completer=bbsengine.sig.getchsigcompleter, args=args)
print(res)
