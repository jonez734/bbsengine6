import argparse

from typing import NamedTuple

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
        self.pk = f"{rec['person_key']}"
        self.content = f"{rec['name_given']} {rec['name_sur']}".ljust(width - 9, " ")
        self.data = rec
        self.width = width
        self.disabled = False

    def help(self):
        io.echo(f"this is a help message in a function")

    def display(self):
        io.echo(
            f"{{/all}}{{cha}} {{engine.menu.cursorcolor}}{{engine.menu.color}} {{engine.menu.boxcharcolor}}{{acs:vline}}{{cic}} {self.content} {{/all}}{{engine.menu.boxcharcolor}}{{acs:vline}}{{engine.menu.shadowcolor}} {{engine.menu.color}} {{/all}}{{cha}}",
            end="",
            flush=True,
        )
        return


class CategoryListboxItem(ListboxItem):
    def __init__(self, category: str, width: int):
        super().__init__()
        self.pk = category
        self.content = category.ljust(width - 9, " ")
        self.data = {"category": category}
        self.width = width
        self.disabled = False

    def display(self):
        io.echo(
            f"{{/all}}{{cha}} {{engine.menu.cursorcolor}}{{engine.menu.color}} {{engine.menu.boxcharcolor}}{{acs:vline}}{{cic}} {self.content} {{/all}}{{engine.menu.boxcharcolor}}{{acs:vline}}{{engine.menu.shadowcolor}} {{engine.menu.color}} {{/all}}{{cha}}",
            end="",
            flush=True,
        )
        return


CATEGORY_TABLES = ["person", "edu", "attractions", "attraction_place", "elector"]


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
    io.setvar("engine.menu.boxcharcolor", "{bglightgray}{darkgreen}")
    io.setvar("engine.menu.color", "{bggray}")
    io.setvar("engine.menu.shadowcolor", "{bgdarkgray}")
    io.setvar("engine.menu.cursorcolor", "{bglightgray}{blue}")
    io.setvar("engine.menu.boxcolor", "{bgblue}{green}")
    io.setvar("engine.menu.titlecolor", "{black}{bglightgray}")
    io.setvar("engine.menu.disableditemcolor", "{darkgray}")
    io.setvar("engine.menu.resultfailedcolor", "{bgred}{white}")

    io.setvar("itemcolor", "{blue}{bglightgray}")
    io.setvar("currentitemcolor", "{bgwhite}{black}")


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
            keycol = get_table_key_column( tbl)
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
                        available.append(atbl)
                        break
        else:
            keycol = get_table_key_column( tbl)
            sql = f"SELECT 1 FROM article2.{tbl} WHERE {keycol} = %s LIMIT 1"
            with database.cursor(conn) as cur:
                cur.execute(sql, (person_key,))
                if cur.rowcount > 0:
                    available.append(tbl)
    return available


def display_person_detail(conn, person_key: str):
    keycol = get_table_key_column( "person")
    sql = f"select * from article2.person where {keycol}=%s"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"there are no presidents in the database")
            return

        person = cur.fetchone()

        util.heading("person")
        io.echo(f"{{labelcolor}}Name: {{valuecolor}}{person['name_common']} {person['name_sur']}")
        date_born = person["date_born"]
        place_born = person["place_born"] if person["place_born"] is not None else ""
        state_born = person["state_born"] if person["state_born"] is not None else ""

        date_die = person["date_die"] if person["date_die"] != "9999-99-99" else "--"
        state_die = person["state_die"] if person["state_die"] != "9999-99-99" else ""
        place_die = person["place_die"] if person["place_die"] is not None else ""

        io.echo(f"{{labelcolor}}Born: {{valuecolor}}{date_born} {place_born} {state_born}")
        io.echo(f"{{labelcolor}}Died: {{valuecolor}}{date_die} {place_die} {state_die}")


def display_edu_detail(conn, person_key: str):
    keycol = get_table_key_column("edu")
    sql = f"select * from article2.edu where {keycol}=%s order by date_start"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no education records")
            return

        util.heading("education")
        for rec in cur.fetchall():
            date_start = rec["date_start"] if rec["date_start"] else ""
            date_end = rec["date_end"] if rec["date_end"] else ""
            institution = rec["institution"] if rec["institution"] else ""
            degree = rec["degree"] if rec["degree"] else ""
            study_field = rec["study_field"] if rec["study_field"] else ""
            io.echo(f"{{valuecolor}}{date_start} - {date_end} {{labelcolor}}{institution} {{valuecolor}}{degree} {{labelcolor}}{study_field}")


def display_attractions_detail(conn, person_key: str):
    keycol = get_table_key_column( "attractions")
    sql = f"select * from article2.attractions where {keycol}=%s order by year"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no attractions records")
            return

        util.heading("attractions")
        for rec in cur.fetchall():
            year = rec["year"] if rec["year"] else ""
            attraction = rec["attraction"] if rec["attraction"] else ""
            location = rec["location"] if rec["location"] else ""
            io.echo(f"{{valuecolor}}{year} {{labelcolor}}{attraction} {{valuecolor}}{location}")


def display_attraction_table_detail(conn, person_key: str, table_name: str, key_col: str | None = None):
    if key_col is None:
        key_col = get_table_key_column(table_name)

    sql = f"select * from article2.{table_name} where {key_col}=%s order by year"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no records in {table_name}")
            return

        util.heading(table_name)
        columns = [desc[0] for desc in cur.description]
        for rec in cur.fetchall():
            row_parts = []
            for col in columns:
                val = rec[col] if rec[col] is not None else ""
                row_parts.append(str(val))
            io.echo(f"{{valuecolor}}{' | '.join(row_parts)}")


def display_elector_detail(conn, person_key: str):
    keycol = get_table_key_column("elector")
    sql = f"select * from article2.elector where {keycol}=%s order by election_year"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no elector records")
            return

        util.heading("elector")
        for rec in cur.fetchall():
            election_year = rec["election_year"] if rec["election_year"] else ""
            electors = rec["electors"] if rec["electors"] else ""
            popular_vote = rec["popular_vote"] if rec["popular_vote"] else ""
            io.echo(f"{{valuecolor}}{election_year} {{labelcolor}}Electors: {{valuecolor}}{electors} {{labelcolor}}Popular: {{valuecolor}}{popular_vote}")


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


def display_attraction_join_detail(conn, person_key: str):
    sql = "select * from article2.attraction_join where person_key=%s"
    dat = (person_key,)
    with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo(f"no records in attraction_join")
            return

        util.heading("attraction_join")
        columns = [desc[0] for desc in cur.description]
        for rec in cur.fetchall():
            row_parts = []
            for col in columns:
                val = rec[col] if rec[col] is not None else ""
                row_parts.append(str(val))
            io.echo(f"{{valuecolor}}{' | '.join(row_parts)}")


def display_category_detail(conn, person_key: str, category: str):
    if category == "person":
        display_person_detail(conn, person_key)
    elif category == "edu":
        display_edu_detail(conn, person_key)
    elif category == "elector":
        display_elector_detail(conn, person_key)
    elif category == "attraction_join":
        display_attraction_join_detail(conn, person_key)
    elif category.startswith("attraction_"):
        display_attraction_table_detail(conn, person_key, category)


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

            with database.connect(args, pool=pool) as conn:
                if args.debug:
                    io.echo(f"connection started", level="debug")

                with database.cursor(conn) as cur:
                    if args.debug:
                        io.echo(f"cursor started", level="debug")
                    cur.execute("select count(distinct person_key) as totalitems from article2.president")
                    res = cur.fetchone()
                    totalitems = res["totalitems"]
                    if args.debug:
                        io.echo(f"{totalitems=}", level="debug")

                sql = "select distinct person_key, name_given, name_sur, name_common from article2.president"
                with database.cursor(conn, scrollable=True, name="presidentlistbox") as cur:
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
                            io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}cancelled")
                            done = True
                        elif op.status == "exit":
                            io.echo(f"{{inputcolor}}exit")
                            return True
                        elif op.status == "selected":
                            if not op.item:
                                return False

                            current_person_key = op.item.pk

                            io.echo(f"selected president {op.item.pk} {op.item.content}")

                            available = get_available_categories(conn, current_person_key)
                            category_items = [
                                CategoryListboxItem(cat, 20) for cat in available
                            ]
                            lb_category.items = category_items
                            lb_category._currentindex = 0
                            lb_category._curpage = 0

                            if args.debug:
                                io.echo(f"categories available: {available}", level="debug")

                            io.echo(f"{{promptcolor}}select a category: ", flush=True, end="")
                            cat_op = lb_category.run("category: ")

                            if cat_op.status == "selected" and cat_op.item:
                                category = cat_op.item.pk
                                io.echo(f"selected category: {category}")

                                display_category_detail(conn, current_person_key, category)

                                io.echo(f"{{promptcolor}}press any key to continue: {{/all}}", flush=True, end="")
                                io.getch()

    except psycopg.DatabaseError as e:
        io.echo(f"demo_listbox_masterdetail.main.100: database error: {e}", level="error")
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
        io.echo(f"{{savecursor}}{{curpos:{io.terminal.height()},0}}{{/all}}{{eraseline}}{{reset}}{{restorecursor}}")
