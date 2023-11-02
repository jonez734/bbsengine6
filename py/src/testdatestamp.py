import os
from time import tzset
import datetime
from dateutil.tz import tzlocal

import bbsengine6 as bbsengine

#from zoneinfo import ZoneInfo

#os.environ["TZ"] = "GMT" # "PST8PDT"
tzset()

#t = datetime.datetime(2023, 8, 7, 13, 24, 27, 708699, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)))
#tz = ZoneInfo("US/Pacific")
#print(tz.tzname())
t = datetime.datetime(2023, 8, 7, 13, 24, 27, 708699, tzinfo=tzlocal()) # , tzinfo=ZoneInfo("US/Pacific")) # datetime.timezone(datetime.timedelta(days=-1, seconds=72000)))
print(bbsengine.util.datestamp(t))
