import os

# import ttyio6 as ttyio
from . import io
import time
from datetime import datetime, timedelta
from dateutil.parser import parse

# import datetime
import dateutil.tz


def add_default_tz(x, tzinfo):
    return x.replace(tzinfo=x.tzinfo or tzinfo)


# @since 20231203 merged from getdate3
def getdate(buf):
    time.tzset()
    #    tz = datetime.tzinfo("US/Pacific") # .tzname # ("US/Pacific")
    localtz = dateutil.tz.tzlocal()

    buf = buf.strip()
    if buf == "now":
        return datetime.now(tz=localtz)
    elif buf == "tomorrow":
        return datetime.now(tz=localtz) + timedelta(days=+1)
    elif buf == "yesterday":
        return datetime.now(tz=localtz) + timedelta(days=-1)
    elif buf == "+2 days" or buf == "2 days":
        return datetime.now(tz=localtz) + timedelta(days=+2)
    elif buf == "-2 days":
        return datetime.now(tz=localtz) + timedelta(days=-2)
    elif buf == "today":
        res = datetime.now(tz=localtz)
        io.echo(f"{res=}", level="debug")
        return datetime.now(tz=localtz)
    elif buf == "last week":
        return datetime.now(tz=localtz) + timedelta(days=-7)
    elif buf == "next week":
        return datetime.now(tz=localtz) + timedelta(days=+7)
    else:
        try:
            res = add_default_tz(parse(buf), localtz)
        except dateutil.parser._parser.ParserError:
            return None
        else:
            return res


def verifyValidDateExpression(buf, **kw):
    if getdate(buf) is not None:
        return True
    return False


def date(args, prompt, value, **kw):
    buf = io.inputstring(prompt, value, verify=verifyValidDateExpression)
    res = getdate(buf)
    if res is None:
        io.echo("invalid date expression")
    return res


# @since 20230923 copied from bbsengine5
def filename(prompt, currentvalue, **kw):
    path = os.path.expanduser(currentvalue)
    path = os.path.expandvars(path)
    #  dirname = os.path.dirname(path)
    #  if dirname is not None and dirname != "":
    #    os.chdir(dirname)
    return io.inputstring(prompt, currentvalue, **kw)
