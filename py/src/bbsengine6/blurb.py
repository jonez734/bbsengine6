import os
from pathlib import Path

from . import database, member, io
from .io.echo import echo


def get_content_dir(args) -> Path:
    content_dir = getattr(args, "blurb_content_dir", None)
    if content_dir is None:
        content_dir = os.environ.get(
            "BBSENGINE6_BLURB_CONTENT_DIR", "/var/bbsengine6/blurb_content"
        )
    return Path(content_dir)


def _safe_content_path(args, contentpath: str) -> Path | None:
    """Resolve contentpath and verify it stays inside the blurb content
    directory. Returns None if the path is unsafe or unreadable.

    Database-stored contentpath comes from member-controlled JSON attributes,
    so it must never escape the configured blurb content dir.
    """
    if not contentpath:
        return None
    try:
        base = get_content_dir(args).resolve()
        candidate = Path(contentpath).resolve()
    except (OSError, ValueError):
        return None
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


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
    if "attributes" in blurb:
        # psycopg3 adapts dict to jsonb automatically; pass-through.
        blurb["attributes"] = blurb["attributes"]
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


def updateattributes(
    args,
    blurbid: int,
    attributes: dict,
    reset: bool = False,
    table: str = "engine.__blurb",
    mogrify: bool = False,
):
    if reset is False:
        sql = "update %s set attributes=attributes||%%s where id=%%s" % (table,)
    else:
        sql = "update %s set attributes=%%s where id=%%s" % (table,)

    if args.debug is True:
        io.echo("updateblurbattributes.120: sql=%s" % (sql), level="debug")

    dat = (attributes, blurbid)

    with database.connect(args) as dbh:
        with database.cursor(dbh) as cur:
            if mogrify is True:
                io.echo(
                    "updateblurbattributes.100: %r"
                    % (cur.mogrify(sql, dat)),
                    level="debug",
                )
            cur.execute(sql, dat)


def update(args, id: int, blurb: dict, reset=False, mogrify=False):
    blurb["dateupdated"] = "now()"
    blurb["updatedbymoniker"] = member.getcurrentid(args)
    attr = blurb["attributes"] if "attributes" in blurb else {}
    if len(attr) > 0:
        updateattributes(args, id, attr, reset=reset, mogrify=mogrify)
        if "attributes" in blurb:
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
        if k in rec:
            blurb[k] = rec[k]

    own_cur = cur is None
    if own_cur:
        with database.connect(args) as dbh:
            with database.cursor(dbh) as cur:
                blurb["flags"] = _fetch_flags(cur, rec.get("id"))
    else:
        blurb["flags"] = _fetch_flags(cur, rec.get("id"))

    return blurb


def _fetch_flags(cur, blurbid) -> dict:
    if blurbid is None:
        return {}
    sql = (
        "SELECT flag.name, "
        "       coalesce(map_blurb_flag.value, flag.defaultvalue) AS value "
        "FROM engine.member_flag "
        "LEFT OUTER JOIN engine.map_blurb_flag "
        "  ON flag.name = engine.map_blurb_flag.name "
        " AND engine.map_blurb_flag.memberid = %s"
    )
    cur.execute(sql, (blurbid,))
    return {row["name"]: row["value"] for row in cur.fetchall()}


def get(args, id: int):
    with database.connect(args) as dbh:
        with database.cursor(dbh) as cur:
            cur.execute("select * from engine.__blurb where id=%s", (id,))
            rec = cur.fetchone()
            if rec is None:
                return None
            return build(args, rec, cur=cur)


def get_with_content(args, id: int) -> dict | None:
    blurb = get(args, id)
    if blurb is None:
        return None

    contentpath = blurb.get("attributes", {}).get("contentpath")
    safe = _safe_content_path(args, contentpath) if contentpath else None
    if safe is not None:
        blurb["content"] = safe.read_text()
    else:
        blurb["content"] = load_content(args, id)

    return blurb


def approve(args, id: int, value: bool = True) -> bool:
    """Set the approved flag on blurb ``id``.

    Persists via engine.map_blurb_flag (the same table build() reads).
    Returns True on success, False on failure.
    """
    approved_str = "true" if value else "false"
    try:
        with database.connect(args) as dbh:
            with database.cursor(dbh) as cur:
                cur.execute(
                    "INSERT INTO engine.map_blurb_flag (memberid, name, value) "
                    "VALUES (%s, 'approved', %s) "
                    "ON CONFLICT (memberid, name) "
                    "DO UPDATE SET value = EXCLUDED.value",
                    (id, approved_str),
                )
        return True
    except Exception as e:
        io.echo_traceback(f"bbsengine6.blurb.approve.100: {e}")
        return False
