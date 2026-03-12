import argparse

import psycopg
from bbsengine6 import io, database


def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("demo_listbox_givenyear")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    parser.add_argument(
        "--year",
        action="store",
        dest="year",
        type=int,
        default=None,
        help="Year to query (optional, will prompt if not provided)",
    )

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
        return "[NEEDINFO]"


def get_presidents_in_office(conn, year: int, excluded_keys: set) -> list[dict]:
    year_str = str(year)
    if excluded_keys:
        placeholders = ",".join(["%s"] * len(excluded_keys))
        sql = f"""
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start, j.date_end
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND j.date_start <= %s
              AND (j.date_end IS NULL OR j.date_end >= %s)
              AND p.person_key NOT IN ({placeholders})
        """
        params = (year_str, year_str, *excluded_keys)
    else:
        sql = """
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start, j.date_end
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND j.date_start <= %s
              AND (j.date_end IS NULL OR j.date_end >= %s)
        """
        params = (year_str, year_str)
    with database.cursor(conn) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_presidents_between_terms(conn, year: int, excluded_keys: set) -> list[dict]:
    year_str = str(year)
    if excluded_keys:
        placeholders = ",".join(["%s"] * len(excluded_keys))
        sql = f"""
            WITH in_office AS (
                SELECT DISTINCT person_key
                FROM article2.job
                WHERE title ILIKE 'n_us_gov_president%%'
                  AND date_start <= %s
                  AND (date_end IS NULL OR date_end >= %s)
            )
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die,
                   (SELECT MAX(j.date_end) FROM article2.job j 
                    WHERE j.person_key = p.person_key 
                      AND j.title ILIKE 'n_us_gov_president%%'
                      AND j.date_end < %s) as date_start,
                   (SELECT MIN(j.date_start) FROM article2.job j 
                    WHERE j.person_key = p.person_key 
                      AND j.title ILIKE 'n_us_gov_president%%'
                      AND j.date_start > 
                        (SELECT MAX(j2.date_end) FROM article2.job j2
                         WHERE j2.person_key = p.person_key 
                           AND j2.title ILIKE 'n_us_gov_president%%'
                           AND j2.date_end < %s)) as date_end
            FROM article2.person p
            WHERE EXISTS (
                SELECT 1 FROM article2.job j1
                JOIN article2.job j2 ON j1.person_key = j2.person_key
                WHERE j1.person_key = p.person_key
                  AND j1.title ILIKE 'n_us_gov_president%%'
                  AND j2.title ILIKE 'n_us_gov_president%%'
                  AND j1.date_end < %s
                  AND j2.date_start > %s
                  AND j1.date_end < j2.date_start
            )
              AND p.person_key NOT IN ({placeholders})
              AND p.person_key NOT IN (SELECT person_key FROM in_office)
        """
        params = (
            year_str,
            year_str,
            year_str,
            year_str,
            year_str,
            year_str,
            *excluded_keys,
        )
    else:
        sql = """
            WITH in_office AS (
                SELECT DISTINCT person_key
                FROM article2.job
                WHERE title ILIKE 'n_us_gov_president%%'
                  AND date_start <= %s
                  AND (date_end IS NULL OR date_end >= %s)
            )
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die,
                   (SELECT MAX(j.date_end) FROM article2.job j 
                    WHERE j.person_key = p.person_key 
                      AND j.title ILIKE 'n_us_gov_president%%'
                      AND j.date_end < %s) as date_start,
                   (SELECT MIN(j.date_start) FROM article2.job j 
                    WHERE j.person_key = p.person_key 
                      AND j.title ILIKE 'n_us_gov_president%%'
                      AND j.date_start > 
                        (SELECT MAX(j2.date_end) FROM article2.job j2
                         WHERE j2.person_key = p.person_key 
                           AND j2.title ILIKE 'n_us_gov_president%%'
                           AND j2.date_end < %s)) as date_end
            FROM article2.person p
            WHERE EXISTS (
                SELECT 1 FROM article2.job j1
                JOIN article2.job j2 ON j1.person_key = j2.person_key
                WHERE j1.person_key = p.person_key
                  AND j1.title ILIKE 'n_us_gov_president%%'
                  AND j2.title ILIKE 'n_us_gov_president%%'
                  AND j1.date_end < %s
                  AND j2.date_start > %s
                  AND j1.date_end < j2.date_start
            )
              AND p.person_key NOT IN (SELECT person_key FROM in_office)
        """
        params = (year_str, year_str, year_str, year_str, year_str, year_str)
    with database.cursor(conn) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_presidents_left_office_alive(conn, year: int, excluded_keys: set) -> list[dict]:
    year_str = str(year)
    if excluded_keys:
        placeholders = ",".join(["%s"] * len(excluded_keys))
        sql = f"""
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start, j.date_end
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND j.date_end < %s
              AND (p.date_die = '9999-99-99' OR p.date_die > %s)
              AND p.person_key NOT IN ({placeholders})
        """
        params = (year_str, year_str, *excluded_keys)
    else:
        sql = """
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start, j.date_end
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND j.date_end < %s
              AND (p.date_die = '9999-99-99' OR p.date_die > %s)
        """
        params = (year_str, year_str)
    with database.cursor(conn) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_future_presidents(conn, year: int, excluded_keys: set) -> list[dict]:
    year_str = str(year)
    if excluded_keys:
        placeholders = ",".join(["%s"] * len(excluded_keys))
        sql = f"""
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND p.date_born <= %s
              AND j.date_start > %s
              AND (p.date_die = '9999-99-99' OR p.date_die > %s)
              AND p.person_key NOT IN ({placeholders})
        """
        params = (year_str, year_str, year_str, *excluded_keys)
    else:
        sql = """
            SELECT DISTINCT p.person_key, p.name_given, p.name_sur, p.name_common,
                   p.date_born, p.date_die, j.date_start
            FROM article2.person p
            JOIN article2.job j ON p.person_key = j.person_key
            WHERE j.title ILIKE 'n_us_gov_president%%'
              AND p.date_born <= %s
              AND j.date_start > %s
              AND (p.date_die = '9999-99-99' OR p.date_die > %s)
        """
        params = (year_str, year_str, year_str)
    with database.cursor(conn) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def display_group(title: str, presidents: list[dict]) -> None:
    io.echo(f"{{titlecolor}}{title}{{/all}}")
    if not presidents:
        io.echo("  none")
    else:
        seen = set()
        for pres in presidents:
            person_key = pres.get("person_key")
            if person_key in seen:
                continue
            seen.add(person_key)
            name = compose_person_name(pres)
            date_start = pres.get("date_start") or ""
            date_end = pres.get("date_end")
            if date_end is None or date_end == "9999-99-99":
                date_end = ""
            io.echo(f"  {name} ({date_start} - {date_end})")


parser = buildargs()


def main(args, **kw):
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

            # screen.init(args)

            with database.connect(args, pool=pool) as conn:
                if args.year is not None:
                    year = args.year
                    if year < 1789 or year > 2030:
                        io.echo(f"Year must be between 1789 and 2030", level="error")
                        return False
                else:
                    year = 0
                    valid = False
                    while not valid:
                        year_str = io.inputinteger(
                            prompt="Enter a year (1789-present): "
                        )
                        if year_str is None:
                            io.echo("cancelled")
                            return False
                        if isinstance(year_str, list):
                            year_str = year_str[0] if year_str else None
                        if year_str is None:
                            io.echo("cancelled")
                            return False
                        try:
                            year = int(year_str)
                            if year < 1789 or year > 2030:
                                io.echo("Year must be between 1789 and 2030")
                                continue
                            valid = True
                        except (ValueError, TypeError):
                            io.echo("Invalid year")
                            continue

                io.echo(f"{{titlecolor}}Presidents in year {year}")

                assigned_keys: set = set()

                io.echo()
                in_office = get_presidents_in_office(conn, year, assigned_keys)
                for key in in_office:
                    assigned_keys.add(key["person_key"])
                display_group("Presidents in office:", in_office)

                io.echo()
                between_terms = get_presidents_between_terms(conn, year, assigned_keys)
                for key in between_terms:
                    assigned_keys.add(key["person_key"])
                display_group("Presidents between terms:", between_terms)

                io.echo()
                left_office_alive = get_presidents_left_office_alive(
                    conn, year, assigned_keys
                )
                for key in left_office_alive:
                    assigned_keys.add(key["person_key"])
                display_group(
                    "Presidents left office and still alive:", left_office_alive
                )

                io.echo()
                future = get_future_presidents(conn, year, assigned_keys)
                display_group("People alive who will become president:", future)

    except psycopg.DatabaseError as e:
        io.echo(f"demo_listbox_givenyear.main.100: database error: {e}", level="error")
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
