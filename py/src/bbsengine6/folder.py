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


# Root sig path prefix. Set to "" to disable 'top.' prefix, "top" to use it (legacy).
ROOT_SIG_PREFIX = ""


# Security: Validate folder path to prevent regex DoS and path traversal attacks
_SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
_SAFE_URI_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")


def _prefix_path(path: str) -> str:
    """Apply ROOT_SIG_PREFIX to a path if configured."""
    prefix = ROOT_SIG_PREFIX
    if prefix and not path.startswith(prefix + ".") and path != prefix:
        return f"{prefix}.{path}"
    return path


def _strip_prefix(path: str) -> str:
    """Remove ROOT_SIG_PREFIX from a path if present."""
    prefix = ROOT_SIG_PREFIX
    if prefix and path.startswith(prefix + "."):
        return path[len(prefix) + 1 :]
    return path


def _validate_path(path: str) -> bool:
    """Validate that path contains only safe characters to prevent ReDoS and path traversal."""
    if not path or len(path) > 256:
        return False
    return _SAFE_PATH_PATTERN.match(path) is not None


def _validate_uri(uri: str) -> bool:
    """Validate that uri contains only safe characters.

    URIs are built from paths (dots replaced with slashes) and may contain
    forward slashes for nested folders. Used with the SQL `=` operator only,
    so the ReDoS concern from the `~` operator does not apply.
    """
    if not uri or len(uri) > 256:
        return False
    return _SAFE_URI_PATTERN.match(uri) is not None


def buildpath(args, path: str) -> str:
    """Convert folder path hyphens to underscores."""
    return path.replace("-", "_")


def builduri(args, path: str) -> str:
    """Build URI from folder path."""
    path = _strip_prefix(path)
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
        "attrs",
        "datecreated",
        "createdbymoniker",
        "dateapproved",
        "approvedbymoniker",
        "dateupdated",
        "updatedbymoniker",
    ):
        if col in row:
            folder[col] = row[col]
    if "attrs" in folder:
        folder["attributes"] = folder.pop("attrs")
    return folder


def buildrow(args, folder):
    row = {}
    old_to_new = {
        "createdbyid": "createdbymoniker",
        "updatedbyid": "updatedbymoniker",
        "approvedbyid": "approvedbymoniker",
        "attributes": "attrs",
    }
    for old_col, new_col in old_to_new.items():
        if old_col in folder:
            folder[new_col] = folder.pop(old_col)
    for col in (
        "path",
        "uri",
        "title",
        "name",
        "intro",
        "attrs",
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

    if cur is not None:
        kwargs["conn"] = cur.connection if hasattr(cur, "connection") else None

    folder["datecreated"] = "now()"
    folder["createdbymoniker"] = member.getcurrentmoniker(args, **kwargs)

    #  if "approved" in sig and sig["approved"] is True:
    #    sig["dateapproved"] = "now()"
    #    sig["approvedbymoniker"] = member.getcurrentmoniker(args)

    insert_kwargs = {"mogrify": mogrify}
    if cur is not None:
        insert_kwargs["conn"] = cur.connection if hasattr(cur, "connection") else None
        insert_kwargs["cur"] = cur
    for key in ("conn", "pool"):
        if key in kwargs:
            insert_kwargs[key] = kwargs[key]

    folder = buildrow(args, folder)

    try:
        return database.insert(
            args,
            "engine.__folder",
            folder,
            returnid=True,
            primarykey="path",
            **insert_kwargs,
        )
    except psycopg.DatabaseError as e:
        io.echo(f"engine.folder.insert.120: database error: {e}", level="error")
        raise


# @since 20260606
def create(args, folder, create_parents: bool = False, **kwargs) -> bool:
    """Create a new folder. Silently skips if folder already exists.

    Args:
        args: argparse namespace with debug, databasename, etc.
        folder: dict with keys - path (required), title, intro, uri, attributes
        create_parents: If True, create any missing ancestor folders
        **kwargs: cur (cursor), conn (connection), pool

    Returns:
        bool: True if folder was created, False if it already exists
    """
    cur = kwargs.get("cur", None)
    path = folder.get("path", "")

    if not _validate_path(path):
        io.echo(
            f"engine.folder.create.050: invalid path: {path!r}",
            level="error",
        )
        return False

    if create_parents is True:
        parts = path.split(".")
        ancestor_paths = [".".join(parts[:i]) for i in range(1, len(parts))]
        for ancestor_path in ancestor_paths:
            if exists(args, ancestor_path, **kwargs) is not True:
                ancestor_folder = {
                    "path": ancestor_path,
                    "title": ancestor_path.split(".")[-1],
                }
                insert_kwargs = dict(kwargs)
                insert_kwargs.pop("cur", None)
                if cur is not None:
                    insert_kwargs["cur"] = cur
                try:
                    insert(args, ancestor_folder, **insert_kwargs)
                except psycopg.DatabaseError as e:
                    io.echo(
                        f"engine.folder.create.110: database error creating ancestor {ancestor_path}: {e}",
                        level="error",
                    )
                    return False

    if exists(args, path, **kwargs) is True:
        io.echo(
            f"engine.folder.create.100: folder {path!r} already exists",
            level="debug",
        )
        return False

    insert_kwargs = dict(kwargs)
    insert_kwargs.pop("cur", None)
    if cur is not None:
        insert_kwargs["cur"] = cur

    try:
        insert(args, folder, **insert_kwargs)
        return True
    except psycopg.DatabaseError as e:
        io.echo(f"engine.folder.create.120: database error: {e}", level="error")
        return False


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

    cur = kwargs.get("cur", None)
    if cur is not None:
        return _work(cur.connection)

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"engine.folder.get.150: {pool=}", level="error")
        return None
    with database.connect(args, pool=pool) as conn:
        return _work(conn)


# @since 20210220
def update(args, path: str, folder: dict, **kwargs) -> bool:
    #  cur = kwargs.get("cur", None)
    #  mogrify = kwargs.get("mogrify", False)
    kwargs.setdefault("primarykey", "path")
    folder = buildrow(args, folder)
    return database.update(
        args, "engine.__folder", path, folder, **kwargs
    )  # mogrify=mogify, cur=cur)


# @since 20250605
def delete(args, path: str, **kwargs) -> bool:
    """Delete a folder by path."""
    if not _validate_path(path):
        io.echo(f"engine.folder.delete.050: invalid path: {path!r}", level="error")
        return False

    conn = kwargs.get("conn", None)
    commit = kwargs.get("commit", True)

    def _work(cur):
        sql = "delete from engine.__folder where path = %s"
        dat = (path,)
        cur.execute(sql, dat)
        return cur.rowcount > 0

    if conn is None:
        with database.connect(args) as conn:
            with database.cursor(conn) as cur:
                result = _work(cur)
                if commit:
                    conn.commit()
                return result
    else:
        with database.cursor(conn) as cur:
            result = _work(cur)
            if commit:
                conn.commit()
            return result


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

        prefix = ROOT_SIG_PREFIX
        if text == "":
            # Return all children of root prefix
            dat = (prefix + ".*{1}" if prefix else "*{1}",)
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
    # Apply ROOT_SIG_PREFIX instead of hardcoding "top."
    prefix = ROOT_SIG_PREFIX
    folders = [
        prefix + "." + s
        if prefix and not s.startswith(prefix + ".") and s != prefix
        else s
        for s in folders
    ]
    return folders


# @since 20230522 check that all sigpaths listed in buffer do not exist
def noneexist(buf: str, **kwargs: dict) -> bool:
    args = kwargs.get("args", None)

    sql = "select 1 from engine.folder where path ~ %s"

    def _work(cur):
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

    cur = kwargs.get("cur", None)
    if cur is not None:
        return _work(cur)

    conn = kwargs.get("conn", None)
    if conn is not None:
        with database.cursor(conn) as cur:
            return _work(cur)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"engine.folder.noneexist.150: {pool=}", level="error")
        return False
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            return _work(cur)


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
    if cur is not None:
        return _work(cur)

    conn = kwargs.get("conn", None)
    if conn is not None:
        with database.cursor(conn) as cur:
            return _work(cur)

    pool = kwargs.get("pool", None)
    args = kwargs.get("args", None)
    if pool is None:
        io.echo(f"engine.folder.allexist.150: {pool=}", level="error")
        return False
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            return _work(cur)


def getchfoldercompleter(word, **kwargs):
    def build(word, **kwargs):
        args = kwargs.get("args", None)

        if not _validate_path(word):
            return

        sql = "select distinct path from engine.folder where path ~ %s"

        prefix = ROOT_SIG_PREFIX
        if word == "":
            dat = (prefix + ".*{1}" if prefix else "*{1}",)
        elif word[-1] == ".":
            dat = (word + "*{1}",)
        else:
            dat = (word + "*",)

        cur = kwargs.get("cur", None)
        if cur is not None:
            if args.debug is True:
                io.echo(f"{database.mogrifysql(cur, sql, dat)=}", level="debug")
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return
            for rec in database.resultiter(cur):
                yield rec["path"]
            return

        conn = kwargs.get("conn", None)
        if conn is not None:
            with database.cursor(conn) as cur:
                if args.debug is True:
                    io.echo(f"{database.mogrifysql(cur, sql, dat)=}", level="debug")
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    return
                for rec in database.resultiter(cur):
                    yield rec["path"]
            return

        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"engine.folder.getchfoldercompleter.150: {pool=}", level="error")
            return
        with database.connect(args, pool=pool) as conn:
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

    def _work(cur):
        for s in buildlist(buf):
            dat: tuple = (s,)
            io.echo(
                f"engine.folder.exists.100: {database.mogrifysql(cur, sql, dat)=}",
                level="debug",
            )
            cur.execute(sql, dat)
            if cur.rowcount == 1:
                io.echo(f"engine.folder.exists.120: {buf=} exists", level="debug")
                return True
            io.echo(
                f"engine.folder.exists.140: {buf=} does not exist",
                level="debug",
            )
            return False
        return False

    if cur is not None:
        return _work(cur)

    conn = kwargs.get("conn", None)
    if conn is not None:
        with database.cursor(conn) as cur:
            return _work(cur)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"engine.folder.exists.150: {pool=}", level="error")
        return False
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            return _work(cur)


def uriexists(args, buf: str, **kwargs: dict) -> bool:
    if not _validate_uri(buf):
        io.echo(f"engine.folder.uriexists.050: invalid uri: {buf!r}", level="error")
        return False

    sql = "select 1 from engine.folder where uri=%s"
    dat = (buf,)

    def _work(cur):
        io.echo(f"engine.folder.uriexists.100: {buf=}", level="debug")
        cur.execute(sql, dat)
        io.echo(
            f"engine.folder.uriexists.120: {database.mogrifysql(cur, sql, dat)=}",
            level="debug",
        )
        if cur.rowcount == 0:
            return False
        return True

    cur = kwargs.get("cur", None)
    if cur is not None:
        return _work(cur)

    conn = kwargs.get("conn", None)
    if conn is not None:
        with database.cursor(conn) as cur:
            return _work(cur)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"engine.folder.uriexists.150: {pool=}", level="error")
        return False
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            return _work(cur)


# @since 20240624
# @project:9294
def striptop(folderpath, top: str = None) -> str:
    if top is None:
        top = ROOT_SIG_PREFIX
    if not top:
        return folderpath
    return folderpath.replace(top, "").strip(".")
