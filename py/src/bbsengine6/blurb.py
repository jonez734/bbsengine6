from . import database, member, io

from psycopg2.extras import Json


def insert(
    args,
    blurb: dict,
    prg: str,
    table: str = "engine.__blurb",
    returnid: bool = True,
    primarykey: str = "id",
    mogrify: bool = False,
):
    blurb["prg"] = prg
    blurb["attributes"] = Json(blurb["attributes"])
    blurb["datecreated"] = "now()"
    blurb["createdbyid"] = member.getcurrentid(args)
    if args.debug is True:
        io.echo(
            f"bbsengine.blurb.insert.100: blurb={blurb!r} table={table!r}",
            level="debug",
        )
    return database.insert(
        args, table, blurb, returnid=returnid, primarykey=primarykey, mogrify=mogrify
    )


def updatesigs(
    args, blurbid: int, sigpaths, completerdelims=", ", mogrify: bool = False
):
    if sigpaths is None or len(sigpaths) == 0:
        return None

    # FIXME: buildsiglist is not defined - function needs to be implemented or removed
    # io.echo(f"bbsengine6.blurb.updatesigs.100: sigpaths={sigpaths!r}", level="debug")
    # sigpaths = buildsiglist(sigpaths)
    # if type(sigpaths) == str:
    #   sigpaths = re.split("|".join(completerdelims), sigpaths)
    #   sigpaths = [s.strip() for s in sigpaths]
    #   sigpaths = [s for s in sigpaths if s]
    return None

    dbh = database.connect(args)
    cur = dbh.cursor()
    sql = "delete from engine.map_blurb_sig where blurbid=%s"
    dat = (blurbid,)
    if mogrify is True:
        io.echo(cur.mogrify(sql, dat), level="debug")

    cur.execute(sql, dat)
    for sigpath in sigpaths:
        io.echo("bbsengine6.blurb.updatesigs.100: sigpath=%r" % (sigpath))
        sigmap = {"blurbid": blurbid, "sigpath": sigpath}
        database.insert(
            args, "engine.map_blurb_sig", sigmap, returnid=False, mogrify=mogrify
        )
    #  dbh.commit()
    return None


def updateattributes(
    args,
    blurbid: int,
    attributes: dict,
    reset: bool = False,
    table: str = "engine.__blurb",
    mogrify: bool = False,
):
    if reset is False:
        sql = "update %s set attributes=attributes||%%s where id=%s" % (table, blurbid)
    else:
        sql = "update %s set attributes=%%s where id=%s" % (table, blurbid)

    if args.debug is True:
        io.echo("updateblurbattributes.120: sql=%s" % (sql), level="debug")

    dat = (Json(attributes),)

    dbh = database.connect(args)
    cur = dbh.cursor()
    if mogrify is True:
        io.echo(
            "updateblurbattributes.100: %r" % (cur.mogrify(sql, dat)), level="debug"
        )
    return cur.execute(sql, dat)


def update(args, id: int, blurb: dict, reset=False, mogrify=False):
    blurb["dateupdated"] = "now()"
    blurb["updatedbyid"] = member.getcurrentid(args)
    attr = blurb["attributes"] if "attributes" in blurb else {}
    if len(attr) > 0:
        updateattributes(args, id, attr, reset=reset, mogrify=mogrify)
        del blurb["attributes"]
    return database.update(args, "engine.__blurb", id, blurb, mogrify=mogrify)


def commit(args):
    return database.commit(args)


def build(args, rec, cur=None):
    blurb = {}
    for k in (
        "id",
        "parentid",
        "prg",
        "attributes",
        "datecreated",
        "createdbymoniker",
        "dateupdated",
        "updatedbymoniker",
        "dateapproved",
        "approvedbymoniker",
    ):
        blurb[k] = rec[k]

    sql = "select flag.name, coalesce(map_blurb_flag.value, flag.defaultvalue) as value from engine.flag left outer join engine.map_blurb_flag on flag.name = engine.map_blurb_flag.name and engine.map_blurb_flag.memberid=%s"
    if cur is None:
        dbh = database.connect(args)
        cur = dbh.cursor()
    dat = (rec.get("id"),)
    cur.execute(sql, dat)
    if cur.rowcount == 0:
        return blurb

    res = cur.fetchall()
    flag = {}
    for f in res:
        flag = {}
        flag[f] = res[f]
    blurb["flags"] = cur.fetchone()

    return blurb


def get(args, id: int):
    sql = "select * from engine.__blurb where id=%s"
    dat = (id,)
    dbh = database.connect(args)
    cur = dbh.cursor()
    cur.execute(sql, dat)
    if cur.rowcount == 0:
        return None
    rec = cur.fetchone()
    blurb = build(args, rec, cur)
    return blurb


def approve(args, id: int, value: str = True):
    blurb = get(args, id)
    blurb["flags"]["approved"] = value
    return True
