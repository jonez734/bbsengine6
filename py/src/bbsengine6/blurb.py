import os
from pathlib import Path

from . import database, member, io
from .io.echo import echo

from psycopg2.extras import Json


def get_content_dir(args) -> Path:
    content_dir = getattr(args, "blurb_content_dir", None)
    if content_dir is None:
        content_dir = os.environ.get(
            "BBSENGINE6_BLURB_CONTENT_DIR", "/var/bbsengine6/blurb_content"
        )
    return Path(content_dir)


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
    blurb["createdbymoniker"] = member.getcurrentid(args)
    if args.debug is True:
        io.echo(
            f"bbsengine.blurb.insert.100: blurb={blurb!r} table={table!r}",
            level="debug",
        )
    return database.insert(
        args, table, blurb, returnid=returnid, primarykey=primarykey, mogrify=mogrify
    )


def save_content(args, blurbid: int, content: str, mogrify: bool = False) -> str:
    content_dir = get_content_dir(args)
    content_dir.mkdir(parents=True, exist_ok=True)

    filepath = content_dir / f"{blurbid}.txt"
    filepath.write_text(content)

    if args.debug is True:
        echo(f"bbsengine6.blurb.save_content.100: saved to {filepath}", level="debug")

    return str(filepath)


def insert_with_content(
    args, blurb: dict, prg: str, content: str | None = None, **kwargs
) -> int:
    blurbid = insert(args, blurb, prg, **kwargs)

    if content is not None and blurbid is not None:
        contentpath = save_content(
            args, blurbid, content, mogrify=kwargs.get("mogrify", False)
        )
        blurb["attributes"]["contentpath"] = contentpath
        updateattributes(
            args,
            blurbid,
            {"contentpath": contentpath},
            mogrify=kwargs.get("mogrify", False),
        )

    return blurbid


def load_content(args, blurbid: int) -> str | None:
    content_dir = get_content_dir(args)
    filepath = content_dir / f"{blurbid}.txt"

    if not filepath.exists():
        return None

    return filepath.read_text()


def delete_content(args, blurbid: int) -> bool:
    content_dir = get_content_dir(args)
    filepath = content_dir / f"{blurbid}.txt"

    if filepath.exists():
        filepath.unlink()
        return True
    return False


def update_with_content(
    args, id: int, blurb: dict, content: str | None = None, **kwargs
) -> int:
    blurbid = update(args, id, blurb, **kwargs)

    if content is not None:
        save_content(args, id, content, mogrify=kwargs.get("mogrify", False))

    return blurbid


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
    blurb["updatedbymoniker"] = member.getcurrentid(args)
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


def get_with_content(args, id: int) -> dict | None:
    blurb = get(args, id)
    if blurb is None:
        return None

    contentpath = blurb.get("attributes", {}).get("contentpath")
    if contentpath and Path(contentpath).exists():
        blurb["content"] = Path(contentpath).read_text()
    else:
        blurb["content"] = load_content(args, id)

    return blurb


def approve(args, id: int, value: str = True):
    blurb = get(args, id)
    blurb["flags"]["approved"] = value
    return True
