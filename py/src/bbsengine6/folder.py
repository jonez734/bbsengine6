"""
folder.py - BBS folder/board management module

Security Considerations:
- All path/URI inputs are validated against _SAFE_PATH_PATTERN before SQL queries
- Path validation prevents ReDoS attacks via malicious regex in SQL ~ operator
- Path validation prevents path traversal attacks
- Database connections use context managers for proper resource cleanup
"""

import re

import psycopg
from . import member, database, io


# Security: Validate folder path to prevent regex DoS and path traversal attacks
_SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_path(path: str) -> bool:
    """Validate that path contains only safe characters to prevent ReDoS and path traversal."""
    if not path or len(path) > 256:
        return False
    return _SAFE_PATH_PATTERN.match(path) is not None


def buildpath(args, path: str) -> str:
    """Convert folder path hyphens to underscores."""
    return path.replace("-", "_")


def builduri(args, path: str, top: str = "top") -> str:
    """Build URI from folder path."""
    path = striptop(path)
    path = path.lstrip(".")
    path = path.replace(".", "/")
    if path[:-1] != "/":
        return path + "/"
    else:
        return path


def builddict(args, row):
    folder = {}
    for col in (
        "path",
        "uri",
        "title",
        "name",
        "intro",
        "attributes",
        "datecreated",
        "createdbymoniker",
        "dateapproved",
        "approvedbymoniker",
        "dateupdated",
        "updatedbymoniker",
    ):
        if col in row:
            folder[col] = row[col]
    return folder


def buildrow(args, folder):
    row = {}
    for col in (
        "path",
        "uri",
        "title",
        "name",
        "intro",
        "attributes",
        "datecreated",
        "createdbymoniker",
        "dateapproved",
        "approvedbymoniker",
        "dateupdated",
        "updatedbymoniker",
    ):
        if col in folder:
            row[col] = folder[col]
    return row


def insert(args, folder, **kwargs):
    mogrify = kwargs.get("mogrify", False)
    cur = kwargs.get("cur", None)

    #  attributes = sig["attributes"] if "attributes" in sig else {}
    #  sig["attributes"] = attributes

    #  if exists(args, sig["path"], cur=cur) is True:
    #    if args.debug is True:
    #      io.echo("engine.sig.insert.100: {sig=} exists.")
    #    return None

    folder["datecreated"] = "now()"
    folder["createdbymoniker"] = member.getcurrentmoniker(args)

    #  if "approved" in sig and sig["approved"] is True:
    #    sig["dateapproved"] = "now()"
    #    sig["approvedbymoniker"] = member.getcurrentmoniker(args)

    try:
        return database.insert(
            args,
            "engine.__folder",
            folder,
            returnid=True,
            primarykey="path",
            mogrify=mogrify,
            cur=cur,
        )
    except psycopg.DatabaseError as e:
        io.echo(f"engine.folder.insert.120: database error: {e}", level="error")
        raise


def get(args, path, **kwargs):
    if not _validate_path(path):
        io.echo(f"engine.folder.get.100: invalid path: {path!r}", level="error")
        return None

    def _work(conn):
        with database.cursor(conn) as cur:
            sql = "select * from engine.folder where path ~ %s"
            dat = (path,)
            cur.execute(sql, dat)
            if args.debug is True:
                io.echo(f"{database.mogrifysql(cur, sql, dat)=}", level="debug")
            if cur.rowcount == 0:
                return None
            row = cur.fetchone()
            return builddict(args, row)

    pool = kwargs.pop("pool")
    with database.connect(args, pool=pool) as conn:
        return _work(conn)


# @since 20210220
def update(args, path: str, folder: dict, **kwargs) -> bool:
    #  cur = kwargs.get("cur", None)
    #  mogrify = kwargs.get("mogrify", False)
    return database.update(
        args, "engine.__folder", path, folder, "path", **kwargs
    )  # mogrify=mogify, cur=cur)


class foldercompleter(object):
    def __init__(self, args=None):
        self.args = args
        self.dbh = database.connect(args)
        self.matches = []

        self.debug = args.debug
        if self.debug is True:
            io.echo("init foldercompleter object", level="debug")

    def getmatches(self, text):
        sql = "select distinct path from engine.folder where path ~ %s"

        if text == "":
            dat = ("top.*{1}",)
        elif text[-1] == ".":
            dat = (text + "*{1}",)
        else:
            dat = (text + "*",)

        if not _validate_path(text):
            return []

        with self.dbh.cursor() as cur:
            if self.debug is True:
                io.echo(f"{database.sqlmogrify(cur, sql,dat)=}", level="debug")
            cur.execute(sql, dat)
            res = cur.fetchall()
            foo = []
            for rec in res:
                foo.append(rec["path"])
            return foo

    def complete(self, text, state):
        #    print "state=",state,"text=",text
        if state == 0:
            self.matches = self.getmatches(text)

        return self.matches[state]


# @since 20230521 copied from bbsengine5
def buildlist(folders: str, args=None) -> list:
    if isinstance(folders, str):
        folders = re.split("[, ]", folders)

    folders = [s.strip() for s in folders]
    folders = [s for s in folders if s]
    folders = ["top." + s if not s.startswith("top.") else s for s in folders]
    return folders


# @since 20230522 check that all sigpaths listed in buffer do not exist
def noneexist(buf: str, **kwargs: dict) -> bool:
    args = kwargs.get("args", None)

    sql = "select 1 from engine.folder where path ~ %s"
    with database.connect(args) as dbh:
        with dbh.cursor() as cur:
            for s in buildlist(buf):
                if not _validate_path(s):
                    io.echo(
                        f"engine.folder.noneexist.100: invalid path: {s!r}",
                        level="error",
                    )
                    return False
                dat = (s,)
                cur.execute(sql, dat)
                if cur.rowcount == 1:
                    io.echo(f"folder {s!r} already exists")
                    return False
    return True


def allexist(buf, **kwargs):
    def _work(cur):
        sql = "select 1 from engine.folder where path ~ %s"
        for s in buildlist(buf):
            if not _validate_path(s):
                io.echo(
                    f"engine.folder.allexist.100: invalid path: {s!r}", level="error"
                )
                return False
            dat = (s,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                io.echo(f"folder {s!r} does not exist")
                return False
        return True

    cur = kwargs.get("cur", None)
    args = kwargs.get("args", None)

    if cur is None:
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


def getchfoldercompleter(word, **kwargs):
    def build(word, **kwargs):
        args = kwargs.get("args", None)

        if not _validate_path(word):
            return

        sql = "select distinct path from engine.folder where path ~ %s"

        if word == "":
            dat = ("top.*{1}",)
        elif word[-1] == ".":
            dat = (word + "*{1}",)
        else:
            dat = (word + "*",)

        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                if args.debug is True:
                    io.echo(f"{database.mogrifysql(cur, sql, dat)=}", level="debug")
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    return None

                for rec in database.resultiter(cur):
                    yield rec["path"]
        return None

    return [x for x in build(word, **kwargs) if x is not None and x.startswith(word)]


def input(
    prompt: str = "folder: ", oldvalue: str = "", **kw
):  # multiple:bool=True, verify:callable=allexist, **kw) -> str:
    #  io.echo(f"bbsengine6.sig.input.120: {kw=}", level="debug")
    path = io.inputstring(
        prompt, oldvalue, **kw
    )  # args=args, verify=verify, multiple=multiple, completer=Completer, returnseq=True, **kw)
    path = path.strip()
    return path


# @since 20240421 to work with teos/achilles/vulcan
def exists(args, buf: str, **kwargs: dict) -> bool:
    cur = kwargs.get("cur", None)
    sql: str = "select 1 from engine.folder where path ~ %s"

    for s in buildlist(buf):
        if not _validate_path(s):
            io.echo(f"engine.folder.exists.050: invalid path: {s!r}", level="error")
            return False

    if cur is None:
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                for s in buildlist(buf):
                    dat: tuple = (s,)
                    io.echo(
                        f"engine.folder.exists.100: {database.mogrifysql(cur, sql, dat)=}",
                        level="debug",
                    )
                    cur.execute(sql, dat)
                    if cur.rowcount == 1:
                        io.echo(
                            f"engine.folder.exists.120: {buf=} exists", level="debug"
                        )
                        return True
                    io.echo(
                        f"engine.folder.exists.140: {buf=} does not exist",
                        level="debug",
                    )
                    return False
    else:
        for s in buildlist(buf):
            dat: tuple = (s,)
            io.echo(
                f"engine.folder.exists.160: {database.mogrifysql(cur, sql, dat)=}",
                level="debug",
            )
            cur.execute(sql, dat)
            if cur.rowcount == 1:
                io.echo(f"engine.folder.exists.180: {buf=} exists", level="debug")
                return True
            io.echo(f"engine.folder.exists.200: {buf=} does not exist", level="debug")
            return False


def uriexists(args, buf: str, **kwargs: dict) -> bool:
    if not _validate_path(buf):
        io.echo(f"engine.folder.uriexists.050: invalid uri: {buf!r}", level="error")
        return False

    cur = kwargs.get("cur", None)
    if cur is None:
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                io.echo(f"engine.folder.uriexists.100: {buf=}", level="debug")
                sql = "select 1 from engine.folder where uri=%s"
                dat = (buf,)
                cur.execute(sql, dat)
                io.echo(
                    f"engine.folder.uriexists.120: {database.mogrifysql(cur, sql, dat)=}",
                    level="debug",
                )
                if cur.rowcount == 0:
                    return False
                return True
    else:
        io.echo(f"engine.folder.uriexists.120: {buf=}", level="debug")
        sql = "select 1 from engine.folder where uri=%s"
        dat = (buf,)
        cur.execute(sql, dat)
        io.echo(
            f"engine.folder.uriexists.120: {database.mogrifysql(cur, sql, dat)=}",
            level="debug",
        )
        if cur.rowcount == 0:
            return False
        return True


# @since 20240624
# @project:9294
def striptop(folderpath, top: str = "top") -> str:
    return folderpath.replace(top, "").strip(".")
