"""
Verify and install required PostgreSQL extensions.

Checks for and installs required PostgreSQL extensions (uuid-ossp, etc.)
needed for the BBS engine to function properly.
"""

from bbsengine6 import io, database

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    conn = kwargs.get("conn", None)
    with database.cursor(conn) as cur:
        for ext in ("pgcrypto", "ltree", "citext"):
            io.echo(
                f"{{var:labelcolor}}extension {{var:valuecolor}}{ext}{{var:labelcolor}}: {{var:valuecolor}}",
                end="",
            )
            if database.extensionavailable(args, ext, cur=cur) is True:
                if database.extensioninstalled(args, ext, cur=cur) is False:
                    if database.creatextension(args, ext, cur=cur) is False:
                        io.echo(f"fail")
                        return False
                    else:
                        io.echo(f"created")
                else:
                    io.echo(f" ok ", level="ok")
            else:
                io.echo(f"not available")
                return False
        conn.commit()
    return True
