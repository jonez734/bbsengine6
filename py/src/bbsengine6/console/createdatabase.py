"""Create a new BBS engine database."""

from bbsengine6 import io, database

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    parser = buildargs(args)
    args = parser.parse_args()
    io.echo(
        f"{{var:labelcolor}}creating database {{var:valuecolor}}{args.databasename}"
    )
    if database.create(args, args.databasename, **kwargs) is False:
        io.echo(f"unable to create database {args.databasename}", level="error")
        return False
    io.echo(f"{{var:valuecolor}}{args.databasename}{{var:labelcolor}} created")
    return True
