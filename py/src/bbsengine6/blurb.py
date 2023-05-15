import ttyio5 as ttyio
from . import database

def insertblurb(args:argparse.Namespace, blurb:dict, table:str="engine.__blurb", returnid:bool=True, primarykey:str="id", mogrify:bool=False):
    dbh = database.connect(args)
    blurb["attributes"] = Json(blurb["attributes"])
    blurb["datecreated"] = "now()"
    blurb["createdbyid"] = getcurrentmemberid(args)
    if args.debug is True:
        ttyio.echo("bbsengine.insertblurb.100: blurb=%r table=%r" % (blurb, table), level="debug")
    return database.insert(dbh, table, blurb, returnid=returnid, primarykey=primarykey, mogrify=mogrify)

def updateblurbsigs(dbh, args:argparse.Namespace, blurbid:int, sigpaths, completerdelims=", ", mogrify:bool=False):
  if sigpaths is None or len(sigpaths) == 0:
    return None

  ttyio.echo("bbsengine6.updateblurbsigs.100: sigpaths=%r" % (sigpaths), level="debug")
  sigpaths = buildsiglist(sigpaths)
#  if type(sigpaths) == str:
#    sigpaths = re.split("|".join(completerdelims), sigpaths)
#    sigpaths = [s.strip() for s in sigpaths]
#    sigpaths = [s for s in sigpaths if s]
  
  # dbh is first arg
  cur = dbh.cursor()
  sql = "delete from engine.map_blurb_sig where blurbid=%s"
  dat = (blurbid,)
  if mogrify is True:
    ttyio.echo(cur.mogrify(sql, dat), level="debug")

  cur.execute(sql, dat)
  for sigpath in sigpaths:
    ttyio.echo("bbsengine6.updateblurbsigs.100: sigpath=%r" % (sigpath))
    sigmap = { "blurbid": blurbid, "sigpath": sigpath }
    database.insert(dbh, "engine.map_blurb_sig", sigmap, returnid=False, mogrify=mogrify)
#  dbh.commit()
  return None

def updateblurbattributes(dbh, args:argparse.Namespace, blurbid:int, attributes:dict, reset:bool=False, table:str="engine.__blurb", mogrify:bool=False):
  if reset is False:
    sql = "update %s set attributes=attributes||%%s where id=%s" % (table, blurbid)
  else:
    sql = "update %s set attributes=%%s where id=%s" % (table, blurbid)

  if args.debug is True:
    ttyio.echo("updateblurbattributes.120: sql=%s" % (sql), level="debug")

  dat = (Json(attributes),)
  if args.debug is True:
    ttyio.echo("bbsengine6.updateblurbattributes.100: dat=%r" % (dat), level="debug")
  cur = dbh.cursor()
  if mogrify is True:
    ttyio.echo("updateblurbattributes.100: %r" % (cur.mogrify(sql, dat)), level="debug")
  return cur.execute(sql, dat)

def updateblurb(dbh, args:argparse.Namespace, id:int, blurb:dict, reset=False, mogrify=False):
  blurb["dateupdated"] = "now()"
  blurb["updatedbyid"] = getcurrentmemberid(args)
  attr = blurb["attributes"] if "attributes" in blurb else {}
  if len(attr) > 0:
    updateblurbattributes(dbh, args, id, attr, reset=reset, mogrify=mogrify)
    del blurb["attributes"]
  return database.update(dbh, "engine.__blurb", id, blurb, mogrify=mogrify)
