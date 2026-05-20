from __future__ import annotations

import copy
import threading

import psycopg
from psycopg import sql

from . import database, io, util


_threadlocal = threading.local()


def _get_thread_id() -> int:
    return threading.get_ident()


ALLOWED_MEMBER_COLUMNS = frozenset(
    [
        "id",
        "loginid",
        "moniker",
        "name",
        "email",
        "password",
        "credits",
        "attrs",
        "flags",
        "ui",
        "refcode",
        "datecreated",
        "createdbyid",
        "dateupdated",
        "updatedbyid",
        "approvedbyid",
        "dateapproved",
        "lastlogin",
        "lastloginfrom",
    ]
)


def _validate_fields(fields: str, allowed: frozenset = ALLOWED_MEMBER_COLUMNS) -> str:
    if fields == "*":
        return fields
    cols = [c.strip() for c in fields.split(",")]
    for col in cols:
        if col not in allowed:
            raise ValueError(f"Invalid column: {col}")
    return fields


# @since 20221113
def buildrec(member):
    """Transform member dict for database operations.

    Removes excluded fields and handles special types (lists, dicts).
    Dict values are kept as dicts (not JSON strings) - JSON serialization
    is handled by database.py via convert_for_jsonb() and psycopg3.

    This is a structural transformation only. The database module handles
    all conversions to psycopg3 types (Jsonb, etc.) when executing queries.
    """
    #  rec = {}
    #  for k in ("credits", "attributes", "id", "name", "email", "password", "datecreated", "createdbyid", "dateupdated", "updatedbyid", "approvedbyid", "dateapproved", "lastlogin", "lastloginfrom"): # , "datecreatedepoch", "lastloginepoch", "dateapprovedepoch", "dateupdatedepoch"): # attributes, datecreated, createdbyid
    #    if k == "attributes":
    #      rec[k] = json.dumps(row[k])
    #    else:
    #      rec[k] = row[k]
    #  return rec

    m = {}
    for k, v in member.items():
        if k in (
            "datecreatedepoch",
            "dateapprovedepoch",
            "dateupdatedepoch",
            "lastloginepoch",
            "attrs",
        ):
            continue
        elif type(v) is dict:
            # Keep dicts as-is. database.update() will call convert_for_jsonb()
            # to wrap them in psycopg3.Jsonb for database storage.
            # Do NOT call json.dumps() here - that was the bug.
            m[k] = v
            continue
        elif k == "ui" and type(v) is list:
            m[k] = ", ".join(v)
            continue
        else:
            m[k] = v
    return m


def build(args, row={}, **kwargs):
    pool = kwargs.get("pool", None)
    io.echo(f"bbsengine.member.build.140: {kwargs=} {pool=}", level="debug")
    if pool is None:
        return None

    moniker = row.get("moniker", None)
    #    io.echo(f"bbsengine.member.build.400: {row=}", level="debug")
    default_values = {
        "refcode": None,
        "flags": getflags(args, moniker, **kwargs),
        #        "id": None,
        "loginid": None,
        "moniker": None,
        "credits": 100,
        "attrs": {},
        #        "emailverified": False,
        #        "dateemailverified": None,
        #        "emailverifiedbymoniker": None,
        "email": None,
        "password": None,
        "datecreated": "now()",
        "ui": [
            "term",
        ],
    }

    member = {}
    for k in default_values.keys():
        #        io.echo(f"bbsengine.member.build.200: {k=}", level="debug")
        if k in row:
            if k == "ui":
                if row["ui"] is not None:
                    import re

                    member["ui"] = sorted(
                        [item.strip() for item in re.split(r"[ ,]+", row["ui"]) if item]
                    )
                else:
                    member["ui"] = None
            else:
                member[k] = row[k]
        else:
            member[k] = default_values[k]

    io.echo(f"bbsengine6.member.build.100: {member=}", level="debug")
    return member


def getcurrentmoniker(args, **kwargs):
    cached = getattr(_threadlocal, "moniker", None)
    if cached is not None:
        return cached

    def _work(conn):
        loginid = util.getcurrentloginid(args, **kwargs)
        if loginid is None:
            return None
        try:
            with database.cursor(conn) as cur:
                sql = "select moniker from engine.member where loginid=%s"
                dat = (loginid,)
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    return None
                row = cur.fetchone()
                moniker = row["moniker"]
                _threadlocal.moniker = moniker
                return moniker
        except psycopg.DatabaseError:
            io.echo_traceback(f"bbsengine6.member.getcurrentmoniker.100:")
            return None

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.member.getcurrentmoniker.120: pool=None", level="error")
            return None
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


def clear_current_moniker_cache() -> None:
    """Clear the thread-local moniker cache.

    Call this after a member updates their own moniker to ensure
    subsequent calls to getcurrentmoniker() fetch fresh data.
    """
    if hasattr(_threadlocal, "moniker"):
        del _threadlocal.moniker


def notifycount(args, **kwargs) -> int | None:
    """Get total unread notification count for current user.

    Returns:
        Number of unread notifications (queue + database), or 0 if not logged in.
        Returns None if no database connection available.
    """
    from bbsengine6 import notify

    moniker = getcurrentmoniker(args, **kwargs)
    if not moniker:
        return 0

    return notify.count(moniker, args=args, **kwargs)


def getcurrentid(args, **kwargs):
    cached = getattr(_threadlocal, "id", None)
    if cached is not None:
        return cached

    def _work(cur):
        loginid = util.getcurrentloginid(args)
        if loginid is None:
            return None
        try:
            sql = "select id from engine.member where loginid=%s"
            dat = (loginid,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            rec = cur.fetchone()
            member_id = rec["id"]
            _threadlocal.id = member_id
            if args.debug is True:
                io.echo(f"getcurrentid.120: {member_id=}", level="debug")
            return member_id
        except psycopg.DatabaseError:
            io.echo_traceback(f"bbsengine6.member.getcurrentid.180:")
            return None

    if args.debug is True:
        io.echo(f"bbsengine6.member.getcurrentid.120: cached={cached}", level="debug")

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            return None
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    else:
        with database.cursor(conn) as cur:
            return _work(cur)


def clear_current_id_cache() -> None:
    """Clear the thread-local member ID cache.

    Call this after a member updates their own ID to ensure
    subsequent calls to getcurrentid() fetch fresh data.
    """
    if hasattr(_threadlocal, "id"):
        del _threadlocal.id


# @since 20170303
# def getcurrentlogin(args):
#  # membermap = {"jam" : 1}
#  loginid = pwd.getpwuid(os.geteuid())[0]
#
#  dbh = database.connect(args)
#  cur = dbh.cursor()
#  sql = "select 1 from engine.member where loginid=%s"
#  dat = (loginid,)
#  cur.execute(sql, dat)
#  if cur.rowcount == 0:
#    return None
#  return loginid


def setcredits(args, amount: int, moniker: str | None = None, **kwargs):
    def _work(conn):
        sql = "update engine.__member set credits=%s where moniker=%s"
        dat = (int(amount), moniker)
        with database.cursor(conn) as cur:
            return cur.execute(sql, dat)

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.setcredits.100: conn=None", level="error")
        return None

    if amount is None or int(amount) < 0:
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo(
                "bbsengine.member.setcredits.120: You do not exist! Go Away!",
                level="error",
            )
            return None

    try:
        return _work(conn)
    except psycopg.DatabaseError:
        io.echo_traceback("bbsengine6.member.setcredits.200:")
        return None


def getcredits(args, membermoniker: str | None = None, **kwargs) -> int | None:
    def _work(conn):
        sql = "select credits from engine.member where moniker=%s"
        dat = (membermoniker,)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            row = cur.fetchone()
            return row["credits"] if "credits" in row else None

    if membermoniker is None:
        membermoniker = getcurrentmoniker(args, **kwargs)
        io.echo(f"bbsengine6.member.getcredits.300: {membermoniker=}", level="debug")
        if membermoniker is None:
            io.echo(
                "bbsengine.member.getcredits.100: You do not exist! Go Away!",
                level="error",
            )
            return None

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(
                    f"bbsengine6.member.getcredits.200: pool is None", level="error"
                )
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except psycopg.DatabaseError:
        io.echo_traceback("bbsengine6.member.getcredits.200:")
        return None


# def getcurrentmembercredits(args:argparse.Namespace) -> int:
#  memberid = getcurrentmemberid(args)
#  return getmembercredits(args, memberid)

# def getname(args, memberid:int=None) -> str:
#  if memberid is None:
#    memberid = getcurrentid(args)
#
#  dbh = database.connect(args)
#  sql = "select name from engine.member where id=%s"
#  dat = (memberid,)
#  cur = dbh.cursor()
#  cur.execute(sql, dat)
#  res = cur.fetchone()
#  if res is not None and "name" in res:
#    return res["name"]
#  return None

# def getcurrentmembername(args:argparse.Namespace) -> str:
#  currentmemberid = getcurrentmemberid(args)
##  ttyio.echo(f"getcurrentmembername.100: currentmemberid={currentmemberid!r}", level="debug")
#  return getmembername(args, currentmemberid)


def update(args, member, moniker: str | None = None, **kwargs):
    """
    Update a member record in a single atomic transaction.

    Handles moniker changes as a special case with correct ordering:
    - If moniker is changing AND flags are being updated:
      1. Update flags FIRST using OLD moniker (guaranteed to exist)
      2. Update member record (PK changes, CASCADE auto-migrates existing flags)
    - If moniker is NOT changing but flags are updated:
      1. Update member record
      2. Update flags with same moniker
    - All database operations kept in single transaction (commit=False)
    - Caller is responsible for final conn.commit() or conn.rollback()

    Why this order matters:
    - Updating flags first with old moniker avoids FK constraint violations
    - Existing flags are guaranteed to exist when we update them
    - After member PK change, CASCADE automatically migrates flag references
    - Flag value changes applied AFTER migration is complete
    - Single transaction ensures atomicity - all succeed or all rollback

    Args:
        args: Application args
        member: Member dict with fields to update (may include 'flags' key)
        moniker: Old moniker (primary key to match). If None, gets current user.
        **kwargs: Optional - conn (required), commit (default False)

    Returns:
        None on success, None on error (exceptions logged)
    """
    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.update.140: conn=None", level="error")
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo("bbsengine.member.update.150: moniker is None", level="error")
            return None

    member_copy = copy.copy(member)
    if "password" in member_copy:
        del member_copy["password"]

    rec = buildrec(member_copy)
    flags_dict = rec.pop("flags", None)

    # Detect if moniker is changing
    new_moniker = rec.get("moniker", None)
    moniker_is_changing = moniker != new_moniker and new_moniker is not None

    try:
        # STEP 1: If moniker is changing AND flags exist, update flags FIRST with OLD moniker
        # This is critical: existing flags are guaranteed to exist with old moniker
        # No FK constraint violations possible
        if moniker_is_changing and flags_dict:
            if not _update_member_flags(
                args, moniker, flags_dict, conn=conn, commit=False
            ):
                io.echo(
                    f"bbsengine6.member.update.160: Failed to update flags for {moniker}",
                    level="error",
                )
                return None

        # STEP 2: Update member record (may include PK change from moniker to new_moniker)
        # If moniker is changing:
        #   - PostgreSQL CASCADE will automatically UPDATE map_member_flag.moniker
        #   - All existing flags migrate from old moniker to new moniker
        # If moniker is NOT changing:
        #   - Regular member update, no flag migration needed
        database.update(
            args,
            "engine.__member",
            moniker,
            rec,
            primarykey="moniker",
            mogrify=True,
            updatepk=True,  # Allow primary key to be updated
            commit=False,  # Keep in transaction; caller manages final commit
            conn=conn,
        )

        # STEP 3: If moniker is NOT changing but flags need updating, do it now
        # (If moniker WAS changing, we already updated flags in Step 1)
        if not moniker_is_changing and flags_dict:
            if not _update_member_flags(
                args, moniker, flags_dict, conn=conn, commit=False
            ):
                io.echo(
                    f"bbsengine6.member.update.170: Failed to update flags for {moniker}",
                    level="error",
                )
                return None

        # Note: Caller (not this function) is responsible for final conn.commit()
        # This keeps the entire member update operation atomic

        # Clear thread-local caches if updating current user
        if moniker == getcurrentmoniker(args, conn=conn):
            clear_current_moniker_cache()
            clear_current_id_cache()

        return None

    except Exception:
        io.echo_traceback("bbsengine6.member.update.120:")
        return None


def getcurrent(args, fields="*", **kwargs) -> dict | None:
    currentid = getcurrentid(args, **kwargs)
    io.echo(f"bbsengine.member.getcurrent.100: {currentid=}", level="debug")
    if currentid is None:
        return None
    return getbyid(args, currentid, fields, **kwargs)


def getbymoniker(
    args, moniker: str | None = None, fields: str = "*", **kwargs
) -> dict | None:
    def _work(cur):
        if moniker is None:
            return None
        validated_fields = _validate_fields(fields)
        sql = f"select {validated_fields}, timezone(tz, lastlogin) from engine.member where moniker=%s"
        dat = (moniker,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            return None
        rec = cur.fetchone()
        io.echo(f"bbsengine.member.getbymoniker.120: {rec=}", level="debug")
        return build(args, rec, **kwargs)

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"bbsengine.member.getbymoniker.100: pool=None", level="error")
        return None

    try:
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.getbymoniker.100:")
        return None


def getbyid(args, memberid: int, fields: str = "*", **kwargs) -> dict | None:
    def _work(cur):
        validated_fields = _validate_fields(fields)
        sql = f"select {validated_fields} from engine.member where id=%s"
        dat = (memberid,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo("bbsengine6.member.getbyid: no rows returned")
            return None
        res = cur.fetchone()
        return build(args, res, **kwargs)

    cur = kwargs.get("cur", None)
    try:
        if cur is None:
            pool = kwargs.get("pool", None)
            with database.connect(args, pool=pool) as conn:
                with database.cursor(conn) as cur:
                    return _work(cur)
        else:
            return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.getbyid.100:")
        return None


def checkflag(
    args, flag: str, moniker: str | None = None, mogrify: bool = False, **kwargs
):
    def _work(conn):
        if moniker is None:
            return None
        sql = "select * from engine.checkflag(%s, %s)"
        dat = (flag, moniker)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            return cur.fetchone()["checkflag"]

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo(
                "bbsengine.member.checkflag.100: You do not exist! Go away!",
                level="error",
            )
            return None

    if flag is None:
        return None

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.checkflag.200: pool=None", level="critical")
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception:
        io.echo_traceback("bbsengine6.member.checkflag.100:")
        return None


def getflags(args, moniker=None, **kwargs):
    io.echo(f"bbsengine.member.getflags.240: {moniker=}", level="debug")

    def _work(conn):
        sql = "select * from engine.getflags(%s)"
        dat = (moniker,)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            flags = {
                flag["name"]: {
                    "description": flag["description"],
                    "value": flag["value"],
                }
                for flag in cur.fetchall()
            }
            io.echo(f"bbsengine.member.getflags.200: {flags=}", level="debug")
            return flags

    io.echo(f"bbsengine.member.getflags.140: {kwargs=}", level="debug")
    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.getflags.200: pool=None", level="error")
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception:
        io.echo_traceback("bbsengine6.member.getflags.100:")
        return None


def _update_member_flags(args, moniker, flags_dict, conn, commit=False) -> bool:
    """
    Helper to manage member flags in map_member_flag table.

    Updates or inserts flag values for a member using atomic UPSERT operations.
    For each flag in flags_dict, atomically updates if it exists or inserts if not.

    Args:
        args: Application args (for debug logging)
        moniker: Member moniker (target moniker)
        flags_dict: Dict of {flag_name: {value: bool, ...}, ...}
        conn: Database connection (must be open)
        commit: If True, commits transaction. If False, keeps it open.

    Returns:
        True on success, False if any flag operation fails (e.g., member doesn't exist)

    Note:
        - Each flag update is atomic (UPSERT operation)
        - If any flag fails, returns False immediately (transaction left intact for rollback)
        - FK constraint violations (member doesn't exist) return False
    """
    if not flags_dict:
        return True

    try:
        for name, data in flags_dict.items():
            io.echo(
                f"bbsengine6.member._update_member_flags: {name=} {data=}",
                level="debug",
            )
            # setflag now returns bool: True on success, False on FK violation
            success = setflag(args, name, data["value"], moniker=moniker, conn=conn)
            if not success:
                io.echo(
                    f"bbsengine6.member._update_member_flags.100: setflag failed for {name}",
                    level="error",
                )
                return False

        if commit is True:
            conn.commit()

        return True

    except Exception as e:
        io.echo_traceback(f"bbsengine6.member._update_member_flags.100: {e}")
        return False


def setflag(args, name, value, **kwargs) -> bool:
    """Set a flag value for a member using atomic UPSERT operation.

    Uses INSERT ... ON CONFLICT to atomically update or insert flag values.
    This ensures a single database operation without DELETE+INSERT fragility.

    Args:
        args: Application args (for debug logging)
        name: Flag name
        value: Flag value (boolean)
        **kwargs: Optional - moniker, mogrify, conn

    Returns:
        True on success
        False if member doesn't exist (FK constraint violation)
        May raise Exception on unexpected database errors
    """
    moniker = kwargs.get("moniker", None)
    mogrify = kwargs.get("mogrify", False)
    conn = kwargs.get("conn", None)

    if moniker is None:
        moniker = getcurrentmoniker(args, conn=conn)
        if moniker is None:
            return False

    util.logentry(f"setflag({name=}, {value=}, {moniker=})")

    try:
        # Use generic database.upsert() for atomic operation
        # This uses INSERT ... ON CONFLICT for atomicity
        result = database.upsert(
            args,
            "engine.map_member_flag",
            {"moniker": moniker, "name": name, "value": value},
            conflict_columns=["moniker", "name"],
            update_columns=["value"],
            mogrify=mogrify,
            commit=False,  # Keep in transaction; caller manages final commit
            conn=conn,
        )

        return result

    except Exception as e:
        # Check if this is a FK constraint violation (member doesn't exist)
        error_msg = str(e)
        if "fk_mmf_membermoniker" in error_msg.lower():
            # Member doesn't exist - this is expected in some cases
            # Return False so caller can handle gracefully
            io.echo(
                f"bbsengine6.member.setflag: FK constraint violated for moniker={moniker}",
                level="warn",
            )
            return False

        # Unexpected error - log and propagate
        io.echo_traceback("bbsengine6.member.setflag.100:")
        raise


# def getflag(args, name, moniker=None, **kwargs):
#  if moniker is None:
#    moniker = getcurrentmoniker(args)
#    if moniker is None:
#      io.echo("You do not exist! Go away!", level="error")
#      return None
#
#  sql = "select flag.name as name, coalesce(mmf.value, flag.defaultvalue) as value from engine.flag left outer join engine.map_member_flag as mmf on flag.name = mmf.name where flag.name=%s"
#  dat = (name,)
#  sql +="  and mmf.moniker=%s"
#  dat.append(moniker)
#
#  try:
#    with database.connect(args, pool=pool) as conn:
#      with database.cursor(conn) as cur:
#        cur.execute(sql, dat)
#        if cur.rowcount == 0:
#          return None
#        rec = cur.fetchone()
#        return rec["value"]
#  except psycopg.DatabaseError as e:
#    io.echo(f"bbsengine6.member.getflag.100: database error: {e}", level="error")
#    raise

# def updateflag(args, flag, **kwargs):
##  mogrify = kwargs.get("mogrify", False)
##  conn = kwargs.get("conn", database.connect(args))
#
#  sql = "update flag set defaultvalue=%s, description=%s where name=%s"
#  dat = (flag["defaultvalue"], flag["description"], flag["name"])
#  try:
#    with database.connect(args, readonly=False) as conn:
#      with database.cursor(conn) as cur:
#        cur.execute(sql, dat)
#        return
#  except psycopg.DatabaseError as e:
#    io.echo(f"bbsengine6.member.updateflag.100: database error: {e}", level="error")
#    raise

# def getflags(args, membermoniker=None):
#    """Retrieves a dictionary of flags for a member.
#
#    Args:
#        args: A dictionary containing database connection parameters.
#        membermoniker (optional): The unique identifier of the member.
#            If None, returns the flags with default values.
#
#    Returns:
#        A dictionary of flags, where the key is the flag name and the value is
#        a dictionary containing the description and the value (either the member-specific value or the default value from the database, converted to True or False as appropriate).
#    """
#
#    sql = """
#        SELECT flag.name, flag.description,
#               coalesce(engine.map_member_flag.value, flag.defaultvalue) AS value
#        FROM engine.flag
#        LEFT OUTER JOIN engine.map_member_flag ON flag.name = engine.map_member_flag.name
#        AND engine.map_member_flag.moniker = %s
#    """
#
#    try:
#        with database.connect(args) as conn:
#          with database.transaction(conn, readonly=True):
#            with database.cursor(conn) as cur:
#                if membermoniker is None:
#                    # Use None as the parameter when membermoniker is None
#                    cur.execute(sql, (None,))
#                else:
#                    cur.execute(sql, (membermoniker,))
#                flags = {}
#                for row in cur.fetchall():
##                    name, description, value = row
#                    if row["value"].lower() in ('t', 'true', '1'):
#                        value = True
#                    else:
#                        value = False
#                    flags[row["name"]] = {"description": row["description"], "value": row["value"]}
#    except psycopg.DatabaseError as e:
#        io.echo(f"bbsengine6.member.getflags.120: Database error: {e}", level="error")
#        raise
#
#    if args.debug is True:
#      io.echo(f"bbsengine6.member.getflags.100: {flags=}", level="debug")
#    return flags


def setpassword(args, plaintextpassword: str, moniker: str, **kwargs):
    def _setpw(cur):
        sql = "update engine.__member set password=crypt(%s, gen_salt('bf')) where moniker=%s"
        dat = (plaintextpassword, moniker)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            return None
        return True

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            io.echo("bbsengine6.setpassword.160: pool=None", level="error")
            return None

        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _setpw(cur)

    with database.cursor(conn) as cur:
        return _setpw(cur)


def checkpassword(
    args, plaintextpassword: str, membermoniker: str | None = None, **kwargs
):
    def _work(cur):
        if membermoniker is None:
            return None
        sql = "select 1 from engine.member where password=crypt(%s, password) and moniker=%s"
        dat = (plaintextpassword, membermoniker)
        cur.execute(sql, dat)
        io.echo(f"{cur.rowcount=}", level="debug")
        return False if cur.rowcount == 0 else True

    if membermoniker is None:
        membermoniker = getcurrentmoniker(args)
        if membermoniker is None:
            io.echo("You do not exist! Go away!", level="error")
            return None

    io.echo(f"{plaintextpassword=} {membermoniker=}", level="debug")
    try:
        cur = kwargs.get("cur", None)
        if cur is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo("bbsengine6.checkpassword.100: pool=None", level="error")
                return None
            with database.connect(args, pool=pool) as conn:
                with database.cursor(conn) as cur:
                    return _work(cur)
        return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.checkpassword.100:")
        return None


def setattrs(args, attrs: dict, moniker=None, **kwargs):
    reset = kwargs.get("reset", False)

    if moniker is None:
        moniker = getcurrentmoniker(args)
        if moniker is None:
            io.echo("You do not exist! Go Away!", level="error")
            return None

    cur = kwargs.get("cur", None)
    if cur is None:
        io.echo("bbsengine.member.setattrs.100: cur=None", level="error")
        return None

    if reset is False:
        q = sql.SQL("update engine.__member set attrs=attrs||%s where moniker=%s")
    else:
        q = sql.SQL("update engine.__member set attrs=%s where moniker=%s")

    dat = (database.Jsonb(attrs), moniker)
    try:
        return cur.execute(q, dat)
    except Exception:
        io.echo_traceback("bbsengine6.member.setattrs.100:")
        return None


def verifyMemberNotFound(args, name, column="loginid", **kwargs):
    io.echo(f"{args=}", level="debug")
    try:
        with database.connect(args, readonly=True) as conn:
            with database.transaction(conn, readonly=True):
                with database.cursor(conn) as cur:
                    sql = f"select 1 from engine.member where {column}=%s"
                    dat = (name,)
                    cur.execute(sql, dat)
                    if cur.rowcount == 0:
                        return True
                    return False
    except Exception:
        io.echo_traceback("bbsengine6.member.verifyMemberNotFound.100:")
        return None


def verifyMemberFound(args, name, **kwargs):
    io.echo(f"verifyMemberFound.100: {kwargs=}", level="debug")
    column = kwargs.get("column", "loginid")
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.verifyMemberFound.160: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)
    try:
        with database.cursor(conn) as cur:
            sql = f"select 1 from engine.member where {column}=%s"
            dat = (name,)
            cur.execute(sql, dat)
            return False if cur.rowcount == 0 else True
    except Exception:
        io.echo_traceback("bbsengine6.member.verifyMemberFound.100:")
        return None


def moniker_exists(args, moniker: str, **kwargs) -> bool | None:
    """Check if a member moniker exists in the database.

    Validates moniker format and checks existence in engine.member table.

    Args:
        args: Application args
        moniker: Member moniker to validate (case-insensitive via citext)
        **kwargs: Optional - pool, conn

    Returns:
        bool: True if moniker exists, False if not, None on error

    Raises:
        ValueError: If moniker format is invalid
            - Empty or None
            - Exceeds 50 characters
            - Contains non-ASCII characters
            - Contains non-printable characters

    Examples:
        >>> moniker_exists(args, "alice", pool=pool)
        True
        >>> moniker_exists(args, "baduser", pool=pool)
        False
        >>> moniker_exists(args, "café")  # raises ValueError
        ValueError: Invalid moniker: contains non-ASCII characters
    """
    # Validate moniker format and content
    if not moniker or not isinstance(moniker, str):
        raise ValueError("Invalid moniker: must be non-empty string")

    if moniker.startswith("@"):
        raise ValueError("Invalid moniker: cannot start with '@'")

    if len(moniker) > 50:
        raise ValueError(f"Invalid moniker: exceeds 50 characters ({len(moniker)})")

    # Validate printable ASCII only (0x20 to 0x7E)
    for i, char in enumerate(moniker):
        code = ord(char)
        # Printable ASCII range: 0x20 (space) to 0x7E (tilde)
        if code < 0x20 or code > 0x7E:
            raise ValueError(
                f"Invalid moniker: contains non-printable character at position {i}: "
                f"{repr(char)} (0x{code:02x}). Only ASCII (0x20-0x7E) allowed."
            )

    # Check existence using existing verifyMemberFound with moniker column
    return verifyMemberFound(args, moniker, column="moniker", **kwargs)


def insert(args, member, **kwargs):
    """
    Insert a new member record.

    Inserts the member into __member table, then inserts any flags via helper function.
    All operations kept in a single transaction (commit=False by default).
    Caller is responsible for final conn.commit() or conn.rollback().

    Transaction semantics:
    1. INSERT into __member (member becomes visible in current transaction)
    2. For each flag in flags_dict: DELETE + INSERT in map_member_flag
    3. FK constraints are satisfied because member exists in same transaction
    4. Caller commits entire operation atomically

    Args:
        args: Application args
        member: Member dict with optional 'flags' key
        **kwargs: Optional - table (default "engine.__member"), conn, commit (default False)

    Returns:
        New moniker on success, False/None on error
    """
    if member is None:
        io.echo(f"bbsengine6.member.insert.120: no member present", level="warn")
        return None

    table = kwargs.get("table", "engine.__member")
    conn = kwargs.get("conn", None)

    cols = copy.copy(member)
    flags_dict = cols.pop("flags", None)

    if "attrs" in cols:
        del cols["attrs"]
        io.echo(f"bbsengine6.insert.140: removed 'attrs' from member")
    if "id" in cols:
        del cols["id"]
        io.echo(f"bbsengine6.insert.200: removed 'id' from member")

    io.echo(f"bbsengine6.member.insert.100: {member=}", level="debug")

    try:
        # Insert member record (commit=False to keep in same transaction)
        moniker = database.insert(
            args,
            table,
            cols,
            commit=False,  # Keep in transaction; caller manages final commit
            **kwargs,
        )

        if not moniker:
            io.echo_traceback("bbsengine6.member.insert.110: database.insert failed")
            return False

        # Handle flags using helper function (same transaction)
        if flags_dict and conn is not None:
            if not _update_member_flags(
                args, moniker, flags_dict, conn=conn, commit=False
            ):
                io.echo_traceback(
                    "bbsengine6.member.insert.130: _update_member_flags failed"
                )
                return False

        return moniker

    except Exception:
        io.echo_traceback("bbsengine6.member.insert.150:")
        return False


def count(args, **kwargs):
    def _work(cur):
        sql = "select count(moniker) from engine.member"
        cur.execute(sql)
        if cur.rowcount == 0:
            return None
        res = cur.fetchone()
        count = res["count"]
        return count

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo("bbsengine6.member.count.100: conn=None", level="error")
        return None
    try:
        with database.cursor(conn) as cur:
            return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.count.100:")
        return None


def group_exists(args, group_name: str, **kwargs) -> bool | None:
    """Check if a group exists in the database.

    Validates group name format and checks existence in engine.__notify_group.

    Args:
        args: Application args
        group_name: Group name to validate (case-sensitive)
        **kwargs: Optional - pool, conn

    Returns:
        bool: True if group exists, False if not, None on error

    Raises:
        ValueError: If group_name format is invalid
            - Empty or None
            - Exceeds 100 characters
            - Contains non-ASCII characters
            - Contains non-printable characters

    Examples:
        >>> group_exists(args, "ops", pool=pool)
        True
        >>> group_exists(args, "nonexistent", pool=pool)
        False
    """
    # Validate group name format
    if not group_name or not isinstance(group_name, str):
        raise ValueError("Invalid group name: must be non-empty string")

    if len(group_name) > 100:
        raise ValueError(
            f"Invalid group name: exceeds 100 characters ({len(group_name)})"
        )

    # Validate printable ASCII only (0x20 to 0x7E)
    for i, char in enumerate(group_name):
        code = ord(char)
        # Printable ASCII range: 0x20 (space) to 0x7E (tilde)
        if code < 0x20 or code > 0x7E:
            raise ValueError(
                f"Invalid group name: contains non-printable character at position {i}: "
                f"{repr(char)} (0x{code:02x}). Only ASCII (0x20-0x7E) allowed."
            )

    # Check existence
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.member.group_exists.100: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)

    try:
        with database.cursor(conn) as cur:
            sql = "SELECT 1 FROM engine.__notify_group WHERE group_name=%s LIMIT 1"
            dat = (group_name,)
            cur.execute(sql, dat)
            return cur.rowcount > 0
    except Exception:
        io.echo_traceback("bbsengine6.member.group_exists.100:")
        return None


def get_group_members(args, group_name: str, **kwargs) -> list[str] | None:
    """Get all member monikers in a group, recursively expanding nested groups.

    Retrieves all members of a notification group from engine.__notify_group,
    recursively expanding any nested groups. Includes cycle detection to prevent
    infinite loops from circular group references.

    Args:
        args: Application args
        group_name: Name of the group
        **kwargs: Optional - pool, conn, _visited (internal: set of visited groups for cycle detection)

    Returns:
        list[str]: List of member monikers in the group (empty list if no members)
        None: On error

    Raises:
        ValueError: If group_name format is invalid or circular reference detected

    Examples:
        >>> get_group_members(args, "ops", pool=pool)
        ["alice", "bob", "charlie"]  # Includes members from nested groups
        >>> get_group_members(args, "ops", pool=pool)
        []  # Empty group
        >>> get_group_members(args, "circular", pool=pool)
        ValueError: Circular group reference detected: circular -> ... -> circular
    """
    # Validate group name (reuse validation from group_exists)
    if not group_name or not isinstance(group_name, str):
        raise ValueError("Invalid group name: must be non-empty string")

    if len(group_name) > 100:
        raise ValueError(
            f"Invalid group name: exceeds 100 characters ({len(group_name)})"
        )

    # Validate printable ASCII only
    for i, char in enumerate(group_name):
        code = ord(char)
        if code < 0x20 or code > 0x7E:
            raise ValueError(
                f"Invalid group name: contains non-printable character at position {i}: "
                f"{repr(char)} (0x{code:02x}). Only ASCII (0x20-0x7E) allowed."
            )

    # Initialize visited set for cycle detection
    visited = kwargs.get("_visited", None)
    if visited is None:
        visited = set()
    else:
        # Make a copy so we don't modify the caller's set
        visited = set(visited)

    # Detect circular references
    if group_name in visited:
        raise ValueError(
            f"Circular group reference detected: {group_name} is already being expanded"
        )

    visited.add(group_name)

    # Get group members
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.member.get_group_members.100: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)

    try:
        with database.cursor(conn) as cur:
            sql = (
                "SELECT member_moniker FROM engine.__notify_group "
                "WHERE group_name=%s ORDER BY member_moniker"
            )
            dat = (group_name,)
            cur.execute(sql, dat)

            if cur.rowcount == 0:
                return []

            members = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    member_moniker = row.get("member_moniker")
                else:
                    member_moniker = row[0]

                if not member_moniker:
                    continue

                # Check if this member is itself a group
                is_nested_group = group_exists(args, member_moniker, conn=conn)

                if is_nested_group:
                    # Recursively expand nested group with cycle detection
                    nested_members = get_group_members(
                        args,
                        member_moniker,
                        conn=conn,
                        _visited=visited,
                    )
                    if nested_members is not None:
                        members.extend(nested_members)
                else:
                    # Regular member (moniker)
                    members.append(member_moniker)

            # Remove duplicates while preserving order
            seen = set()
            unique_members = []
            for member in members:
                if member not in seen:
                    seen.add(member)
                    unique_members.append(member)

            return unique_members
    except ValueError:
        # Re-raise validation errors (like circular reference detection)
        raise
    except Exception:
        io.echo_traceback("bbsengine6.member.get_group_members.100:")
        return None
