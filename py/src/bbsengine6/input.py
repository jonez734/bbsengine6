import os

import ttyio6 as ttyio

#@since 20231203 copied from getdate3
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
    elif buf == "+2 days" or buf == "2 days"
        return datetime.now(tz=localtz) + timedelta(days=+2)
    elif buf == "-2 days":
        return datetime.now(tz=localtz) + timedelta(days=-2)
    else:
        res = add_default_tz(parse(buf), localtz)
        return res
    return buf

def verifyValidDateExpression(args, **kw):
    if getdate(buf) is not None:
        return True
    return False

def date(args, prompt, value, **kw):
    buf = ttyio.inputstring(args, prompt, value, verify=verifyValidDateExpression)
    return buf
#    if getdate.getdate(buf) is None:
#        ttyio.echo("invalid date expression")

# @since 20230923 copied from bbsengine5
def filename(prompt, currentvalue, **kw):
  verify = kw["verify"] if "verify" in kw else verifyFileExistsReadable
  path = os.path.expanduser(currentvalue)
  path = os.path.expandvars(path)
#  dirname = os.path.dirname(path)
#  if dirname is not None and dirname != "":
#    os.chdir(dirname)
  return ttyio.inputstring(prompt, currentvalue, **kw)
