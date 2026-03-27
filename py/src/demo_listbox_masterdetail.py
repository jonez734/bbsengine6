import argparse

from typing import NamedTuple, cast

import psycopg
from bbsengine6 import io, util, database, screen
from bbsengine6.listboxcursor import ListboxCursor
from bbsengine6.listbox import Listbox, ListboxItem

NAME = "jam"
HEIGHT = 193.04  # yummy = 166 cm


class Height(NamedTuple):
    cm: float
    feet: float
    inches: float


def cmtofeet(cm: float) -> Height:
    inches = cm / 2.54
    feet = inches // 12
    inches -= feet * 12
    return Height(cm, feet, inches)


class PresidentListboxItem(ListboxItem):
    def __init__(self, rec: dict, width: int, height=1):
        super().__init__()
        self.status = ""
        self.pk = rec['person_key']
        self.content = f"{rec['name_given']} {rec['name_sur']}".ljust(width - 9, " ")
        self.data = rec
        self.width = width
        self.disabled = False
##        common.logentry("PresidentListboxItem._init.100: trace", level="debug")

    def help(self):
        io.echo(f"this is a help message in a function")

#    def display(self, listbox: "Listbox", highlighted: bool):
#        common.logentry("PresidentListboxItem.display.100: trace", level="debug")
#        io.echo(
#            f"{{/all}}{{cha}} {{engine.menu.cursorcolor}}{{engine.menu.color}} {{engine.menu.boxcharcolor}}{{acs:vline}}{{cic}} {self.content} {{/all}}{{engine.menu.boxcharcolor}}{{acs:vline}}{{engine.menu.shadowcolor}} {{engine.menu.color}} {{/all}}{{cha}}",
#            end="",
#            flush=True,
#        )
#        return


class CategoryListboxItem(ListboxItem):
    def __init__(self, category: str, width: int):
        super().__init__()
        self.pk = category
        self.content = category.ljust(width - 9, " ")
        self.data = {"category": category}
        self.width = width
        self.disabled = False

    def display(self, listbox: "Listbox", highlighted: bool):
        io.echo(
            f"{{/all}}{{cha}} {{engine.menu.cursorcolor}}{{engine.menu.color}} {{engine.menu.boxcharcolor}}{{acs:vline}}{{cic}} {self.content} {{/all}}{{engine.menu.boxcharcolor}}{{acs:vline}}{{engine.menu.shadowcolor}} {{engine.menu.color}} {{/all}}{{cha}}",
            end="",
            flush=True,
        )
        return


CATEGORY_TABLES = ["person", "edu", "attractions", "attraction_place", "elector"]


def display_column_value(col_name: str, value, args) -> str | None:
    if value is None:
        if hasattr(args, "debug") and args.debug:
            return ""
        return None
    return value


def buildargs(args=None, **kw):
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
            f"{{warncolor}}warning: no name found for person_key {person.get('person_key', 'unknown')}",
            level="warn",
        )
        return "[NEEDINFO]"


def setbottombar(args, left: str) -> None:
    """Set the bottom bar with left side and preserve right side based on debug flag."""
    right = "[debug]" if args.debug else ""
    io.screen.setbottombar(left, right)


TABLE_KEY_COLUMNS = {
    "person": "person_key",
    "president": "person_key",
    "edu": "person_key",
    "places": "person_key",
    "elector": "person",
    "attractions": "person_key",
    "attraction_hour": "key",
    "attraction_place": "place_key",
    "attraction_social_media": "place_key",
    "attraction_join": "person_key",
}


def get_table_key_column(table_name: str) -> str:
    return TABLE_KEY_COLUMNS.get(table_name, "person_key")


def get_attraction_tables(conn) -> list[tuple[str, str]]:
    tables = []
    sql = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'article2'
        AND table_name LIKE 'attraction_%'
        ORDER BY table_name
    """
    with database.cursor(conn) as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            tbl = row["table_name"]
            keycol = get_table_key_column(tbl)
            tables.append((tbl, keycol))
    return tables


def get_available_categories(conn, person_key: str) -> list[str]:
    available = []
    for tbl in CATEGORY_TABLES:
        if tbl == "attractions":
            attraction_tables = get_attraction_tables(conn)
            for atbl, keycol in attraction_tables:
                sql = f"SELECT 1 FROM article2.{atbl} WHERE {keycol} = %s LIMIT 1"
                with database.cursor(conn) as cur:
                    cur.execute(sql, (person_key,))
                    if cur.rowcount > 0:
                        available.append("attractions")
                        break
        else:
            keycol = get_table_key_column(tbl)
            sql = f"SELECT 1 FROM article2.{tbl} WHERE {keycol} = %s LIMIT 1"
            with database.cursor(conn) as cur:
                cur.execute(sql, (person_key,))
                if cur.rowcount > 0:
                    available.append(tbl)
    return available


def display_person_detail(args, conn, person_key: str):
    keycol = get_table_key_column("person")
    sql = f"select * from article2.person where {keycol}=%s"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"there are no presidents in the database")
            return

        person = cur.fetchone()

        util.heading("person")

        name_common = display_column_value("name_common", person["name_common"], args)
        name_sur = display_column_value("name_sur", person["name_sur"], args)
        if name_common is not None and name_sur is not None:
            io.echo(f"{{labelcolor}}Name: {{valuecolor}}{name_common} {name_sur}")

        date_born = display_column_value("date_born", person["date_born"], args)
        place_born = display_column_value("place_born", person["place_born"], args)
        state_born = display_column_value("state_born", person["state_born"], args)

        if date_born is not None or place_born is not None or state_born is not None:
            parts = [p for p in [date_born, place_born, state_born] if p]
            if parts:
                io.echo(f"{{labelcolor}}Born: {{valuecolor}}{' '.join(parts)}")

        date_die = person["date_die"] if person["date_die"] != "9999-99-99" else None
        if date_die is None and hasattr(args, "debug") and args.debug:
            date_die = ""
        state_die = person["state_die"] if person["state_die"] != "9999-99-99" else None
        if state_die is None and hasattr(args, "debug") and args.debug:
            state_die = ""
        place_die = display_column_value("place_die", person["place_die"], args)

        if date_die is not None or place_die is not None or state_die is not None:
            die_parts = [p for p in [date_die, place_die, state_die] if p]
            if die_parts:
                io.echo(f"{{labelcolor}}Died: {{valuecolor}}{' '.join(die_parts)}")


def display_edu_detail(args, conn, person_key: str):
    keycol = get_table_key_column("edu")
    sql = f"select * from article2.edu where {keycol}=%s order by date_start"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no education records")
            return

        columns = [desc[0] for desc in cur.description]
        edu_items = []
        for rec in cur.fetchall():
            institution = rec["institution"] if rec["institution"] else ""
            content = institution
            item = ListboxItem(content=content, pk=rec)
            edu_items.append(item)

    if len(edu_items) == 1:
        rec = edu_items[0].pk
        util.heading("education")
        for col in columns:
            val = display_column_value(col, rec[col], args)
            if val is not None:
                io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")
    else:
        lb_edu = Listbox(
            args,
            "education",
            itemsperpage=10,
            itemheight=1,
            items=edu_items,
        )

        edu_op = lb_edu.run("select an education: ")

        if edu_op.status == "selected" and edu_op.item:
            util.heading("education")
            rec = edu_op.item.pk
            for col in columns:
                val = display_column_value(col, rec[col], args)
                if val is not None:
                    io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")


def display_attractions_detail(args, conn, person_key: str):
    keycol = get_table_key_column("attractions")
    sql = f"select * from article2.attractions where {keycol}=%s"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no attractions records")
            return

        columns = [desc[0] for desc in cur.description]
        attraction_items = []
        for rec in cur.fetchall():
            attraction = rec["attraction"] if rec["attraction"] else ""
            content = attraction
            item = ListboxItem(content=content, pk=rec)
            attraction_items.append(item)

    if len(attraction_items) == 1:
        rec = attraction_items[0].pk
        util.heading("attraction")
        for col in columns:
            val = display_column_value(col, rec[col], args)
            if val is not None:
                io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")
    else:
        lb_attractions = Listbox(
            args,
            "attractions",
            itemsperpage=10,
            itemheight=1,
            items=attraction_items,
        )

        attr_op = lb_attractions.run("select an attraction: ")

        if attr_op.status == "selected" and attr_op.item:
            util.heading("attraction")
            rec = attr_op.item.pk
            for col in columns:
                val = display_column_value(col, rec[col], args)
                if val is not None:
                    io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")


def display_attraction_table_detail(
    args, conn, person_key: str, table_name: str, key_col: str | None = None
):
    if key_col is None:
        key_col = get_table_key_column(table_name)

    sql = f"select * from article2.{table_name} where {key_col}=%s"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no records in {table_name}")
            return

        columns = [desc[0] for desc in cur.description]
        table_items = []
        for rec in cur.fetchall():
            first_col = rec[columns[0]] if rec[columns[0]] else ""
            content = str(first_col)
            item = ListboxItem(content=content, pk=rec)
            table_items.append(item)

    if len(table_items) == 1:
        rec = table_items[0].pk
        util.heading(table_name)
        for col in columns:
            val = display_column_value(col, rec[col], args)
            if val is not None:
                io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")
    else:
        lb_table = Listbox(
            args,
            table_name,
            itemsperpage=10,
            itemheight=1,
            items=table_items,
        )

        table_op = lb_table.run("select a record: ")

        if table_op.status == "selected" and table_op.item:
            util.heading(table_name)
            rec = table_op.item.pk
            for col in columns:
                val = display_column_value(col, rec[col], args)
                if val is not None:
                    io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")


def display_elector_detail(args, conn, person_key: str):
    keycol = get_table_key_column("elector")
    sql = f"select * from article2.elector where {keycol}=%s order by date"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no elector records")
            return

        columns = [desc[0] for desc in cur.description]
        elector_items = []
        for rec in cur.fetchall():
            election_date = rec["date"] if rec["date"] else ""
            content = election_date
            item = ListboxItem(content=content, pk=rec)
            elector_items.append(item)

    if len(elector_items) == 1:
        rec = elector_items[0].pk
        util.heading("elector")
        for col in columns:
            val = display_column_value(col, rec[col], args)
            if val is not None:
                io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")
    else:
        lb_electors = Listbox(
            args,
            "electors",
            itemsperpage=10,
            itemheight=1,
            items=elector_items,
        )

        elector_op = lb_electors.run("select an elector: ")

        if elector_op.status == "selected" and elector_op.item:
            util.heading("elector")
            rec = elector_op.item.pk
            for col in columns:
                val = display_column_value(col, rec[col], args)
                if val is not None:
                    io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")


def get_attraction_join_keys(conn) -> list[str]:
    sql = """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'article2'
        AND table_name = 'attraction_join'
    """
    with database.cursor(conn) as cur:
        cur.execute(sql)
        columns = [row["column_name"] for row in cur.fetchall()]

    return [c for c in columns if c.endswith("_key")]


def display_attraction_join_detail(args, conn, person_key: str):
    attraction_items = []

    place_sql = "select place_key from article2.attraction_join where person_key=%s"
    with database.cursor(conn) as cur:
        cur.execute(place_sql, (person_key,))
        place_keys = [row["place_key"] for row in cur.fetchall()]

    if place_keys:
        if len(place_keys) == 1:
            sql = "select * from article2.attraction_place where place_key = %s"
            dat = (place_keys[0],)
        else:
            placeholders = ",".join(["%s"] * len(place_keys))
            sql = f"select * from article2.attraction_place where place_key IN ({placeholders})"
            dat = tuple(place_keys)

        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            for rec in cur.fetchall():
                title = rec["title"] if rec["title"] else ""
                item = ListboxItem(
                    content=f"place: {title}",
                    pk={"table": "attraction_place", "rec": rec},
                )
                attraction_items.append(item)

    if not attraction_items:
        io.echo(f"no attraction records")
        return

    if len(attraction_items) == 1:
        item_data = attraction_items[0].pk
        table = item_data["table"]
        rec = item_data["rec"]
        columns = item_data.get("columns", list(rec.keys()))
        util.heading(table)
        for col in columns:
            val = display_column_value(col, rec[col], args)
            if val is not None:
                io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")
    else:
        lb_attractions = Listbox(
            args,
            "attractions",
            itemsperpage=10,
            itemheight=1,
            items=attraction_items,
        )

        attr_op = lb_attractions.run("select an attraction: ")

        if attr_op.status == "selected" and attr_op.item:
            item_data = attr_op.item.pk
            table = item_data["table"]
            rec = item_data["rec"]
            columns = item_data.get("columns", list(rec.keys()))
            util.heading(table)
            for col in columns:
                val = display_column_value(col, rec[col], args)
                if val is not None:
                    io.echo(f"{{labelcolor}}{col}: {{valuecolor}}{val}")

            if table == "attraction_place":
                place_key = rec.get("place_key")
                if place_key:
                    hours_sql = "select * from article2.attraction_hour where key = %s"
                    with database.cursor(conn) as cur:
                        cur.execute(hours_sql, (place_key,))
                        hours_columns = (
                            [desc[0] for desc in cur.description]
                            if cur.description
                            else []
                        )
                        if cur.rowcount > 0:
                            util.heading("attraction_hour")
                            for hour_rec in cur.fetchall():
                                for col in hours_columns:
                                    val = display_column_value(col, hour_rec[col], args)
                                    if val is not None:
                                        io.echo(
                                            f"{{labelcolor}}{col}: {{valuecolor}}{val}"
                                        )
                        else:
                            util.heading("attraction_hour")
                            io.echo(f"{{valuecolor}}needinfo")

                    social_sql = "select * from article2.attraction_social_media where place_key = %s"
                    with database.cursor(conn) as cur:
                        cur.execute(social_sql, (place_key,))
                        if cur.rowcount > 0:
                            util.heading("attraction_social_media")
                            for social_rec in cur.fetchall():
                                url = display_column_value(
                                    "url", social_rec.get("url"), args
                                )
                                if url is not None:
                                    io.echo(f"{{labelcolor}}url: {{valuecolor}}{url}")
                                link_text = display_column_value(
                                    "link_text", social_rec.get("link_text"), args
                                )
                                if link_text is not None:
                                    io.echo(
                                        f"{{labelcolor}}link_text: {{valuecolor}}{link_text}"
                                    )
                                note = display_column_value(
                                    "note", social_rec.get("note"), args
                                )
                                if note is not None:
                                    io.echo(f"{{labelcolor}}note: {{valuecolor}}{note}")


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


parser = buildargs()


def main(args, **kw):
    prompt = "demo_listbox_masterdetail: "
    try:
        with database.getpool(args, dbname="postgres") as pool:
            if not database.exists(args, args.databasename, pool=pool):
                io.echo(f"database '{args.databasename}' does not exist", level="error")
                return False
            if args.debug:
                io.echo(f"postgres database exists", level="debug")

        with database.getpool(args, dbname=args.databasename) as pool:
            if not database.schemaexists(args, "article2", pool=pool):
                io.echo(f"schema 'article2' does not exist", level="error")
                return False
            if args.debug:
                io.echo(f"schema article2 exists", level="debug")

            screen.init(args)
            setbottombar(args, "article2")

            with database.connect(args, pool=pool) as conn:
                if args.debug:
                    io.echo(f"connection started", level="debug")

                with database.cursor(conn) as cur:
                    if args.debug:
                        io.echo(f"cursor started", level="debug")
                    cur.execute(
                        "select count(distinct person_key) as totalitems from article2.president"
                    )
                    res = cur.fetchone()
                    totalitems = res["totalitems"]
                    if args.debug:
                        io.echo(f"{totalitems=}", level="debug")

                sql = "select distinct person_key, name_given, name_sur, name_common from article2.president"
                with database.cursor(
                    conn, scrollable=True, name="presidentlistbox"
                ) as cur:
                    if args.debug:
                        io.echo(f"Executing query", level="debug")
                    cur.execute(sql)
                    if args.debug:
                        io.echo(f"Query executed", level="debug")
                    if cur.rowcount == 0:
                        io.echo(f"no presidents")
                        return None

                    lb_president = ListboxCursor(
                        args,
                        "presidents",
                        itemsperpage=20,
                        itemheight=1,
                        cur=cur,
                        totalitems=totalitems,
                        itemclass=PresidentListboxItem,
                    )
                    if args.debug:
                        io.echo(f"ListboxCursor created", level="debug")

                    lb_category = Listbox(
                        args,
                        "details",
                        itemsperpage=10,
                        itemheight=1,
                        items=[],
                    )

                    current_person_key = None

                    done = False
                    while not done:
                        if args.debug:
                            io.echo(f"about to call lb_president.run", level="debug")
                        op = lb_president.run(prompt)
                        if args.debug:
                            io.echo(f"lb_president.run returned: {op}", level="debug")

                        if op.status == "noitems":
                            io.echo(f"no items")
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
                                CategoryListboxItem(cat, 20) for cat in available
                            ]
                            lb_category.items = cast(list[ListboxItem], category_items)
                            lb_category._currentindex = 0
                            lb_category._curpage = 0

                            if args.debug:
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
