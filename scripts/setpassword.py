from bbsengine6.console.lib import buildargs
from bbsengine6 import database, member
args = buildargs().parse_args([])
pool = database.getpool(args)
try:
    member.setpassword(args, "12345", "jam", pool=pool)
    print("set; verifying:", member.checkpassword(args, "12345", membermoniker="jam", pool=pool))
finally:
    pool.close()
