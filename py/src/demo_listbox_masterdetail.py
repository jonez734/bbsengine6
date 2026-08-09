import argparse

import psycopg
from psycopg import sql

from bbsengine6 import io, util, database, screen
from bbsengine6.listboxcursor import ListboxCursor
from bbsengine6.listbox import Listbox, ListboxItem


class PresidentListboxItem(ListboxItem):
    def __init__(self, rec: dict, width: int, height=1):
        super().__init__()
        self.pk = rec["person_key"]
        self.content = compose_person_name(rec)
        self.data = rec
        self.width = width
        self.disabled = False


CATEGORY_TABLES = ["person", "edu", "attractions", "attraction_place", "elector"]

TABLE_KEY_COLUMNS = {
    "person": "person_key",
    "president": "person_key",
    "edu": "person_key",
    "elector": "person",
    "attraction_join": "person_key",
    "attraction_place": "place_key",
    "attraction_social_media": "place_key",
    "attraction_hour": "key",
}

# Tables whose rows are keyed by place_key and are only reachable from a
# person through article2.attraction_join (person_key -> place_key).
PLACE_KEYED_TABLES = {"attraction_place", "attraction_social_media", "attraction_hour"}


def get_table_key_column(table_name: str) -> str:
    return TABLE_KEY_COLUMNS.get(table_name, "person_key")


def table_has_person(conn, table_name: str, person_key: str) -> bool:
    keycol = get_table_key_column(table_name)
    query = sql.SQL(
        "select 1 from {schema}.{table} where {key} = %s limit 1"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier(table_name),
        key=sql.Identifier(keycol),
    )
    with database.cursor(conn) as cur:
        cur.execute(query, (person_key,))
        return cur.fetchone() is not None


def table_has_place(conn, table_name: str, place_keys: list[str]) -> bool:
    if not place_keys:
        return False
    keycol = get_table_key_column(table_name)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in place_keys)
    query = sql.SQL(
        "select 1 from {schema}.{table} where {key} in ({placeholders}) limit 1"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier(table_name),
        key=sql.Identifier(keycol),
        placeholders=placeholders,
    )
    with database.cursor(conn) as cur:
        cur.execute(query, place_keys)
        return cur.fetchone() is not None


def get_person_place_keys(conn, person_key: str) -> list[str]:
    query = sql.SQL(
        "select place_key from {schema}.{table} where person_key = %s"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("attraction_join"),
    )
    with database.cursor(conn) as cur:
        cur.execute(query, (person_key,))
        return [row["place_key"] for row in cur.fetchall()]


def get_available_categories(conn, person_key: str) -> list[str]:
    place_keys = get_person_place_keys(conn, person_key)
    available = []
    for category in CATEGORY_TABLES:
        if category == "attractions":
            if place_keys:
                available.append(category)
        elif category in PLACE_KEYED_TABLES:
            if table_has_place(conn, category, place_keys):
                available.append(category)
        else:
            if table_has_person(conn, category, person_key):
                available.append(category)
    return available


def display_value(value, args) -> str | None:
    if value is None:
        if getattr(args, "debug", False):
            return ""
        return None
    return value


def display_record_columns(args, rec: dict, heading: str | None = None) -> None:
    if heading is not None:
        util.heading(heading)
    for col, value in rec.items():
        val = display_value(value, args)
        if val is not None:
            io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")


def pick_record(
    args,
    conn,
    *,
    title: str,
    query,
    params,
    heading: str,
    prompt: str,
    empty_msg: str,
    content_key: str | None = None,
):
    """Show one record directly or a listbox to pick one; return (heading, rec) or None."""
    with database.cursor(conn) as cur:
        cur.execute(query, params)
        recs = cur.fetchall()
    if not recs:
        io.echo(empty_msg)
        return None
    if content_key is None:
        content_key = list(recs[0].keys())[0]
    if len(recs) == 1:
        return heading, recs[0]
    items = [
        ListboxItem(content=str(rec.get(content_key) or ""), pk=rec) for rec in recs
    ]
    lb = Listbox(args, title, itemsperpage=10, itemheight=1, items=items)
    op = lb.run(prompt)
    if op.status == "selected" and op.item:
        return heading, op.item.pk
    return None


def compose_person_name(person: dict) -> str:
    """Compose a display name from available name parts."""
    name_common = person.get("name_common")
    name_given = person.get("name_given")
    name_sur = person.get("name_sur")

    if name_common and name_sur:
        return f"{name_common} {name_sur}"
    elif name_given and name_sur:
        return f"{name_given} {name_sur}"
    elif name_sur:
        return name_sur
    elif name_common:
        return name_common
    elif name_given:
        return name_given
    else:
        io.echo(
            f"warning: no name found for person_key {person.get('person_key', 'unknown')}",
            level="warn",
        )
        return "[NEEDINFO]"


def setbottombar(args, left: str) -> None:
    """Set the bottom bar with left side and preserve right side based on debug flag."""
    right = "[debug]" if getattr(args, "debug", False) else ""
    io.screen.setbottombar(left, right)


def display_person_detail(args, conn, person_key: str):
    query = sql.SQL("select * from {schema}.{table} where person_key = %s").format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("person"),
    )
    with database.cursor(conn) as cur:
        cur.execute(query, (person_key,))
        person = cur.fetchone()
        if person is None:
            io.echo("no person record")
            return

        util.heading("person")

        name_common = display_value(person["name_common"], args)
        name_sur = display_value(person["name_sur"], args)
        if name_common is not None and name_sur is not None:
            io.echo(f"{{labelcolor}}Name: {{valuecolor}}{name_common} {name_sur}")

        date_born = display_value(person["date_born"], args)
        place_born = display_value(person["place_born"], args)
        state_born = display_value(person["state_born"], args)

        if date_born is not None or place_born is not None or state_born is not None:
            parts = [p for p in [date_born, place_born, state_born] if p]
            if parts:
                io.echo(f"{{labelcolor}}Born: {{valuecolor}}{' '.join(parts)}")

        date_die = person["date_die"] if person["date_die"] != "9999-99-99" else None
        if date_die is None and getattr(args, "debug", False):
            date_die = ""
        state_die = person["state_die"] if person["state_die"] != "9999-99-99" else None
        if state_die is None and getattr(args, "debug", False):
            state_die = ""
        place_die = display_value(person["place_die"], args)

        if date_die is not None or place_die is not None or state_die is not None:
            die_parts = [p for p in [date_die, place_die, state_die] if p]
            if die_parts:
                io.echo(f"{{labelcolor}}Died: {{valuecolor}}{' '.join(die_parts)}")


def display_edu_detail(args, conn, person_key: str):
    query = sql.SQL(
        "select * from {schema}.{table} where person_key = %s order by date_start"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("edu"),
    )
    result = pick_record(
        args,
        conn,
        title="education",
        query=query,
        params=(person_key,),
        heading="education",
        prompt="select an education: ",
        empty_msg="no education records",
        content_key="institution",
    )
    if result is not None:
        heading, rec = result
        display_record_columns(args, rec, heading)


def display_elector_detail(args, conn, person_key: str):
    query = sql.SQL(
        "select * from {schema}.{table} where {key} = %s order by date"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("elector"),
        key=sql.Identifier(get_table_key_column("elector")),
    )
    result = pick_record(
        args,
        conn,
        title="electors",
        query=query,
        params=(person_key,),
        heading="elector",
        prompt="select an elector: ",
        empty_msg="no elector records",
        content_key="date",
    )
    if result is not None:
        heading, rec = result
        display_record_columns(args, rec, heading)


def display_attraction_hours(args, conn, place_key: str):
    query = sql.SQL("select * from {schema}.{table} where {key} = %s").format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("attraction_hour"),
        key=sql.Identifier(get_table_key_column("attraction_hour")),
    )
    with database.cursor(conn) as cur:
        cur.execute(query, (place_key,))
        hours = cur.fetchall()

    util.heading("attraction_hour")
    if not hours:
        io.echo(f"{{valuecolor}}needinfo")
        return
    for hour_rec in hours:
        display_record_columns(args, hour_rec)


def display_attraction_social_media(args, conn, place_key: str):
    query = sql.SQL(
        "select * from {schema}.{table} where {key} = %s"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("attraction_social_media"),
        key=sql.Identifier(get_table_key_column("attraction_social_media")),
    )
    with database.cursor(conn) as cur:
        cur.execute(query, (place_key,))
        rows = cur.fetchall()

    if not rows:
        return
    util.heading("attraction_social_media")
    for rec in rows:
        display_record_columns(args, rec)


def display_attraction_join_detail(args, conn, person_key: str):
    place_keys = get_person_place_keys(conn, person_key)
    if not place_keys:
        io.echo("no attraction records")
        return

    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in place_keys)
    query = sql.SQL(
        "select * from {schema}.{table} where {key} in ({placeholders})"
    ).format(
        schema=sql.Identifier("article2"),
        table=sql.Identifier("attraction_place"),
        key=sql.Identifier("place_key"),
        placeholders=placeholders,
    )
    result = pick_record(
        args,
        conn,
        title="attractions",
        query=query,
        params=place_keys,
        heading="attraction_place",
        prompt="select an attraction: ",
        empty_msg="no attraction records",
        content_key="title",
    )
    if result is None:
        return
    heading, rec = result
    display_record_columns(args, rec, heading)

    place_key = rec.get("place_key")
    if not place_key:
        return
    display_attraction_hours(args, conn, place_key)
    display_attraction_social_media(args, conn, place_key)


def display_attraction_table_detail(args, conn, person_key: str, table_name: str):
    keycol = get_table_key_column(table_name)
    if table_name in PLACE_KEYED_TABLES:
        place_keys = get_person_place_keys(conn, person_key)
        if not place_keys:
            io.echo(f"no records in {table_name}")
            return
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in place_keys)
        query = sql.SQL(
            "select * from {schema}.{table} where {key} in ({placeholders})"
        ).format(
            schema=sql.Identifier("article2"),
            table=sql.Identifier(table_name),
            key=sql.Identifier(keycol),
            placeholders=placeholders,
        )
        params = place_keys
    else:
        query = sql.SQL("select * from {schema}.{table} where {key} = %s").format(
            schema=sql.Identifier("article2"),
            table=sql.Identifier(table_name),
            key=sql.Identifier(keycol),
        )
        params = (person_key,)

    result = pick_record(
        args,
        conn,
        title=table_name,
        query=query,
        params=params,
        heading=table_name,
        prompt="select a record: ",
        empty_msg=f"no records in {table_name}",
    )
    if result is not None:
        heading, rec = result
        display_record_columns(args, rec, heading)


def display_category_detail(args, conn, person_key: str, category: str):
    if category == "person":
        display_person_detail(args, conn, person_key)
    elif category == "edu":
        display_edu_detail(args, conn, person_key)
    elif category == "elector":
        display_elector_detail(args, conn, person_key)
    elif category == "attractions":
        display_attraction_join_detail(args, conn, person_key)
    elif category.startswith("attraction_"):
        display_attraction_table_detail(args, conn, person_key, category)


def buildargs():
    parser = argparse.ArgumentParser("demo_listbox_masterdetail")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {
        "databasename": "yummyjam",
        "databasehost": "127.0.0.1",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargs(parser, defaults)
    return parser


def init():
    io.setvar("listbox.boxcolor", "{darkgreen}")
    io.setvar("listbox.titlecolor", "{inverse}")
    io.setvar("listbox.item.normal", "{white}")
    io.setvar("listbox.item.highlighted", "{listbox.item.normal}{inverse}")
    io.setvar("listbox.item.disabled", "{darkgray}")
    io.setvar("listbox.bgcolor", "")


parser = buildargs()


def main(args, **kw):
    prompt = "demo_listbox_masterdetail: "
    try:
        with database.getpool(args, dbname="postgres") as pool:
            if not database.exists(args, args.databasename, pool=pool):
                io.echo(f"database '{args.databasename}' does not exist", level="error")
                return False
            if getattr(args, "debug", False):
                io.echo(f"postgres database exists", level="debug")

        with database.getpool(args, dbname=args.databasename) as pool:
            if not database.schemaexists(args, "article2", pool=pool):
                io.echo(f"schema 'article2' does not exist", level="error")
                return False
            if getattr(args, "debug", False):
                io.echo(f"schema article2 exists", level="debug")

            screen.init(args)
            setbottombar(args, "article2")

            with database.connect(args, pool=pool) as conn:
                if getattr(args, "debug", False):
                    io.echo(f"connection started", level="debug")

                with database.cursor(conn) as cur:
                    if getattr(args, "debug", False):
                        io.echo(f"cursor started", level="debug")
                    cur.execute(
                        "select count(distinct person_key) as totalitems from article2.president"
                    )
                    res = cur.fetchone()
                    totalitems = res["totalitems"]
                    if getattr(args, "debug", False):
                        io.echo(f"{totalitems=}", level="debug")

                if totalitems == 0:
                    io.echo("no presidents")
                    return None

                sql_query = "select distinct person_key, name_given, name_sur, name_common from article2.president"
                # Client-side cursor: ListboxCursor pages over it via cur.scroll(),
                # and the detail lookups below run on the same connection.
                with database.cursor(conn) as cur:
                    if getattr(args, "debug", False):
                        io.echo(f"Executing query", level="debug")
                    cur.execute(sql_query)
                    if getattr(args, "debug", False):
                        io.echo(f"Query executed", level="debug")

                    lb_president = ListboxCursor(
                        args,
                        "presidents",
                        itemsperpage=20,
                        itemheight=1,
                        cur=cur,
                        totalitems=totalitems,
                        itemclass=PresidentListboxItem,
                    )
                    if getattr(args, "debug", False):
                        io.echo(f"ListboxCursor created", level="debug")

                    lb_category = Listbox(
                        args,
                        "details",
                        itemsperpage=10,
                        itemheight=1,
                        items=[],
                    )

                    done = False
                    while not done:
                        if getattr(args, "debug", False):
                            io.echo(f"about to call lb_president.run", level="debug")
                        op = lb_president.run(prompt)
                        if getattr(args, "debug", False):
                            io.echo(f"lb_president.run returned: {op}", level="debug")

                        if op.status == "noitems":
                            io.echo("no items")
                            done = True
                        elif op.status == "cancelled":
                            io.echo(
                                f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}cancelled"
                            )
                            done = True
                        elif op.status == "exit":
                            io.echo(f"{{inputcolor}}exit")
                            return True
                        elif op.status == "selected":
                            if not op.item:
                                return False

                            current_person_key = op.item.pk
                            president_name = compose_person_name(op.item.data)

                            io.echo(
                                f"selected president {op.item.pk} {op.item.content}"
                            )
                            setbottombar(args, f"article2 | {president_name}")

                            available = get_available_categories(
                                conn, current_person_key
                            )
                            category_items = [
                                ListboxItem(content=category, pk=category)
                                for category in available
                            ]
                            lb_category.set_items(category_items)

                            if getattr(args, "debug", False):
                                io.echo(
                                    f"categories available: {available}", level="debug"
                                )

                            category_done = False
                            while not category_done:
                                setbottombar(
                                    args,
                                    f"article2 | {president_name} | select category",
                                )
                                cat_op = lb_category.run("category: ")

                                if cat_op.status == "selected" and cat_op.item:
                                    category = cat_op.item.pk
                                    io.echo(f"selected category: {category}")
                                    setbottombar(
                                        args,
                                        f"article2 | {president_name} | {category}",
                                    )

                                    display_category_detail(
                                        args, conn, current_person_key, category
                                    )

                                    io.echo(
                                        f"{{promptcolor}}press any key to continue: {{/all}}",
                                        flush=True,
                                        end="",
                                    )
                                    io.getch()
                                    io.echo()
                                else:
                                    category_done = True
            setbottombar(args, "article2")

    except psycopg.DatabaseError as e:
        io.echo(
            f"demo_listbox_masterdetail.main.100: database error: {e}", level="error"
        )
        return False


if __name__ == "__main__":
    init()

    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        io.echo(f"{{/all}}{{restorecursor}}*INTR*")
    except EOFError:
        io.echo(f"{{/all}}{{restorecursor}}*EOF*")
    finally:
        io.echo(
            f"{{savecursor}}{{curpos:{io.terminal.height()},0}}{{/all}}{{eraseline}}{{reset}}{{restorecursor}}"
        )
