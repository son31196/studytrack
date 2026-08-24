"""Google Calendar integration: fetch + parse a secret ICS feed into simple events.

The secret URL is stored in a git-ignored file (.gcal-url) — local-only, never
committed or published. Parsing covers what class schedules need: plain events,
WEEKLY/DAILY/MONTHLY/YEARLY recurrence with INTERVAL/COUNT/UNTIL/BYDAY, EXDATE,
and RECURRENCE-ID overrides.
"""
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def fetch(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "StudyTrack/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text)


def _parse_prop(line: str):
    head, _, value = line.partition(":")
    parts = head.split(";")
    params = dict(p.partition("=")[::2] for p in parts[1:])
    return parts[0].upper(), params, value


def _parse_dt(params: dict, value: str):
    """Returns (naive local datetime, is_all_day)."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value, "%Y%m%d"), True
    if value.endswith("Z"):
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone().replace(tzinfo=None), False
    # TZID-qualified or floating: keep the wall-clock time as written
    return datetime.strptime(value, "%Y%m%dT%H%M%S"), False


def _parse_vevent(block: str):
    ev = {"exdates": set()}
    for line in block.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        name, params, value = _parse_prop(line)
        if name == "EXDATE":
            for v in value.split(","):
                try:
                    ev["exdates"].add(_parse_dt(params, v)[0].date())
                except ValueError:
                    pass
        elif name in ("DTSTART", "RECURRENCE-ID"):
            try:
                ev[name] = _parse_dt(params, value)
            except ValueError:
                return None
        elif name in ("SUMMARY", "RRULE", "UID", "STATUS"):
            ev[name] = value
    if "DTSTART" not in ev or "SUMMARY" not in ev:
        return None
    return ev


def _occurrences(ev, window_start: date, window_end: date):
    """Expand one event's dates within the window."""
    dtstart, _ = ev["DTSTART"]
    first = dtstart.date()
    if "RRULE" not in ev:
        return [first] if window_start <= first <= window_end else []

    rule = dict(p.partition("=")[::2] for p in ev["RRULE"].split(";"))
    freq = rule.get("FREQ", "")
    interval = max(int(rule.get("INTERVAL") or 1), 1)
    count = int(rule["COUNT"]) if rule.get("COUNT") else None
    until = None
    if rule.get("UNTIL"):
        try:
            # Take the date portion as written — converting the UTC form to
            # local time can land a day early and drop the final occurrence.
            until = datetime.strptime(rule["UNTIL"][:8], "%Y%m%d").date()
        except ValueError:
            pass

    def gen():
        if freq == "WEEKLY":
            bydays = sorted(WEEKDAYS[d] for d in rule.get("BYDAY", "").split(",") if d in WEEKDAYS) or [first.weekday()]
            week0 = first - timedelta(days=first.weekday())
            for w in range(0, 400):
                ws = week0 + timedelta(weeks=w * interval)
                for wd in bydays:
                    d = ws + timedelta(days=wd)
                    if d >= first:
                        yield d
        elif freq == "DAILY":
            for i in range(0, 2000):
                yield first + timedelta(days=i * interval)
        elif freq == "MONTHLY":
            for i in range(0, 120):
                y, m = divmod(first.month - 1 + i * interval, 12)
                try:
                    yield date(first.year + y, m + 1, first.day)
                except ValueError:
                    continue
        elif freq == "YEARLY":
            for i in range(0, 20):
                try:
                    yield date(first.year + i * interval, first.month, first.day)
                except ValueError:
                    continue
        else:
            yield first

    out = []
    n = 0
    for d in gen():
        n += 1
        if count is not None and n > count:
            break
        if (until and d > until) or d > window_end:
            break
        if d >= window_start:
            out.append(d)
    return out


def events_between(ics_text: str, window_start: date, window_end: date) -> list:
    text = _unfold(ics_text)
    vevents = [v for v in (_parse_vevent(b) for b in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S)) if v]

    # Instances rescheduled in Google carry RECURRENCE-ID; exclude those dates
    # from the master series so they don't appear twice.
    overridden = {}
    for ev in vevents:
        if "RECURRENCE-ID" in ev:
            overridden.setdefault(ev.get("UID"), set()).add(ev["RECURRENCE-ID"][0].date())

    out = []
    for ev in vevents:
        if ev.get("STATUS") == "CANCELLED":
            continue
        skip = set(ev["exdates"])
        if "RECURRENCE-ID" not in ev:
            skip |= overridden.get(ev.get("UID"), set())
        dtstart, allday = ev["DTSTART"]
        prefix = "" if allday else dtstart.strftime("%H:%M") + " "
        summary = ev["SUMMARY"].replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")
        for d in _occurrences(ev, window_start, window_end):
            if d not in skip:
                out.append({"date": d.isoformat(), "label": prefix + summary, "type": "gcal"})
    out.sort(key=lambda e: (e["date"], e["label"]))
    return out
