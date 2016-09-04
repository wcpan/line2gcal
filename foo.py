import parsedatetime as pdt
import datetime
import time
import shlex
import argparse
from datetime import datetime as dt
from time import mktime


def parseDatetime(str):
    global start
    c = pdt.Constants()
    p = pdt.Calendar()
    result, r = p.parse(str)
    start = dt.fromtimestamp(mktime(result))


parseDatetime("1d")
minutes = 60
end = start + datetime.timedelta(minutes=minutes)

print(start.isoformat())
print(end.isoformat())
# parser = argparse.ArgumentParser
# parser.parse_args()
