"""(Pro) Show a note only during a time window.

Enter a range like ``09:00-17:00``. If the end is earlier than the start it
wraps past midnight (e.g. ``22:00-06:00`` = 10pm to 6am).
"""

from datetime import datetime

NAME = "time_of_day"
LABEL = "Time of day (Pro)"
PRO = True


def _mins(t):
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def matches(pattern, context):
    if not pattern or "-" not in pattern:
        return False
    try:
        a, b = pattern.split("-", 1)
        start, end = _mins(a), _mins(b)
    except Exception:
        return False
    now = datetime.now()
    cur = now.hour * 60 + now.minute
    if start <= end:
        return start <= cur < end
    return cur >= start or cur < end       # range wraps past midnight


def suggest(context):
    return "09:00-17:00"
