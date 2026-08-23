import sys

from bbsengine6.console.lib import buildargs
from bbsengine6 import database, io, member
args = buildargs().parse_args([])
pool = database.getpool(args)
try:
    result = member.setpassword(args, "12345", "jam", pool=pool)
    if result is not True:
        io.echo(
            "setpassword: no row updated for moniker 'jam' "
            "(does the member exist?)",
            level="error",
        )
        sys.exit(1)
    verify = member.checkpassword(args, "12345", membermoniker="jam", pool=pool)
    io.echo(f"set; verifying: {verify}")
finally:
    pool.close()
