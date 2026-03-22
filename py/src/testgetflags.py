import time
import locale
import argparse

from bbsengine6 import io, database, member


def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("testcheckflag")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)

    return parser


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    time.tzset()

    parser = buildargs()
    args = parser.parse_args()

    io.echo(f"{member.getflags(args, 'JONZ')=}")
