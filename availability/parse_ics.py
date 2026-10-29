"""Create sanitized, read-only busy-time snapshots from one private iCal feed.

Only a GitHub repository secret holds the calendar subscription URL. Never print it,
commit it, embed it in HTML, or publish any VEVENT metadata such as descriptions,
UIDs, titles, locations, or attendee names.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

from icalendar import Calendar
import recurring_ical_events

ZONE = ZoneInfo("America/St_Johns")
HORIZON_DAYS = 400
MAX_FEED_BYTES = 5_000_000
MAX_OCCURRENCES = 10_000


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Calendar endpoint redirected unexpectedly; no availability published")


def normalize_private_url(raw: str) -> str:
    raw = raw.strip()
    if raw.lower().startswith("webcal://"):
        raw = "https://" + raw[len("webcal://"):]
    parsed = urlsplit(raw)
    # Prevent the private subscription token being sent to unexpected hosts.
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("Unsupported private calendar URL")
    host = (parsed.hostname or "").lower()
    if host == "api.band.us":
        if not parsed.path.startswith("/ical") or not parsed.query:
            raise ValueError("BAND calendar subscription URL is invalid")
    elif host in ("calendar.google.com", "www.google.com"):
        if not parsed.path.startswith("/calendar/ical/") or not parsed.path.endswith(".ics"):
            raise ValueError("Google calendar iCal subscription URL is invalid")
    else:
        raise ValueError("Calendar feed must use the official Google or BAND iCal endpoint")
    return urlunsplit(parsed)

def download_ics(private_url: str) -> bytes:
    request = Request(private_url, headers={"Accept": "text/calendar", "User-Agent": "NLBTAvailability/1.0"})
    # Reject 301/302: never pass a private token to another host.
    with build_opener(RejectRedirects()).open(request, timeout=20) as response:
        content = response.read(MAX_FEED_BYTES + 1)
    if len(content) > MAX_FEED_BYTES:
        raise ValueError("Calendar feed exceeds safe size")
    if b"BEGIN:VCALENDAR" not in content or b"END:VCALENDAR" not in content:
        raise ValueError("Invalid iCalendar feed")
    return content


def to_local(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=ZONE) if value.tzinfo is None else value.astimezone(ZONE)
    return datetime.combine(value, time.min, tzinfo=ZONE)


def event_interval(event) -> tuple[datetime, datetime]:
    if "DTSTART" not in event:
        raise ValueError("Calendar event missing start time")
    start = event.decoded("DTSTART")
    if "DTEND" in event:
        end = event.decoded("DTEND")
    elif "DURATION" in event:
        end = start + event.decoded("DURATION")
    elif isinstance(start, date) and not isinstance(start, datetime):
        end = start + timedelta(days=1)
    else:
        # Timed events with a missing end are still potentially bookings.
        # Treat as zero-duration and conservatively block the entire day.
        end = start
    start_local, end_local = to_local(start), to_local(end)
    if end_local <= start_local:
        # BAND sometimes exports empty or reversed time ranges.
        # Ignoring such an event would falsely label a booked date available.
        # A zero-length event blocks its whole calendar day; a reversed event
        # blocks that day and the next, conservatively covering overnight use.
        day = datetime.combine(start_local.date(), time.min, tzinfo=ZONE)
        days = 1 if end_local == start_local else 2
        return day, datetime.combine(start_local.date() + timedelta(days=days), time.min, tzinfo=ZONE)
    return start_local, end_local


def normalize_malformed_events(cal: Calendar) -> None:
    """Repair malformed BAND intervals BEFORE recurrence expansion.

    The recurrence library silently reverses some inverted DTSTART/DTEND pairs.
    If we waited until after expansion, that could mark the late-night booking
    window as free. Instead mark the whole affected date(s) occupied.
    """
    for event in cal.walk("VEVENT"):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if str(event.get("TRANSP", "")).upper() == "TRANSPARENT":
            continue
        if "DTSTART" not in event:
            raise ValueError("Calendar event missing DTSTART")
        original_start = event.decoded("DTSTART")
        if "DTEND" in event:
            original_end = event.decoded("DTEND")
        elif "DURATION" in event:
            original_end = original_start + event.decoded("DURATION")
        elif isinstance(original_start, date) and not isinstance(original_start, datetime):
            continue
        else:
            original_end = original_start
        start_local = to_local(original_start)
        end_local = to_local(original_end)
        if end_local > start_local:
            continue
        days = 1 if end_local == start_local else 2
        day = start_local.date()
        all_day = isinstance(original_start, date) and not isinstance(original_start, datetime)
        new_start = day if all_day else datetime.combine(day, time.min, tzinfo=ZONE)
        new_end_date = day + timedelta(days=days)
        new_end = new_end_date if all_day else datetime.combine(new_end_date, time.min, tzinfo=ZONE)
        for key in ("DTSTART", "DTEND", "DURATION"):
            if key in event:
                del event[key]
        event.add("DTSTART", new_start)
        event.add("DTEND", new_end)


def make_snapshot(ics_bytes: bytes, now_utc: datetime) -> dict:
    now_local = now_utc.astimezone(ZONE)
    first_date = now_local.date()
    last_date = first_date + timedelta(days=HORIZON_DAYS)
    window_start = datetime.combine(first_date, time.min, tzinfo=ZONE)
    window_end = datetime.combine(last_date + timedelta(days=1), time.min, tzinfo=ZONE)

    cal = Calendar.from_ical(ics_bytes)
    if str(cal.get("VERSION", "")) != "2.0":
        raise ValueError("Invalid iCalendar format")
    normalize_malformed_events(cal)

    occurrences = recurring_ical_events.of(cal).between(window_start, window_end)
    if len(occurrences) > MAX_OCCURRENCES:
        raise ValueError("Calendar contains too many occurrences")

    daily: dict[str, list[list[int]]] = defaultdict(list)
    for event in occurrences:
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if str(event.get("TRANSP", "")).upper() == "TRANSPARENT":
            continue
        start, end = event_interval(event)
        day = max(first_date, start.date())
        through = min(last_date, end.date())
        while day <= through:
            midnight = datetime.combine(day, time.min, tzinfo=ZONE)
            next_midnight = datetime.combine(day + timedelta(days=1), time.min, tzinfo=ZONE)
            if start < next_midnight and end > midnight:
                a = max(start, midnight)
                b = min(end, next_midnight)
                start_min = a.hour * 60 + a.minute
                end_min = 1440 if b >= next_midnight else b.hour * 60 + b.minute
                if start_min < end_min:
                    daily[day.isoformat()].append([start_min, end_min])
            day += timedelta(days=1)

    # Merge intervals: do not expose names, IDs, event counts or overlapping records.
    merged: dict[str, list[list[int]]] = {}
    for day, intervals in sorted(daily.items()):
        combined: list[list[int]] = []
        for start, end in sorted(intervals):
            if combined and start <= combined[-1][1]:
                combined[-1][1] = max(combined[-1][1], end)
            else:
                combined.append([start, end])
        merged[day] = combined

    return {
        "version": 1,
        "timezone": "America/St_Johns",
        "generated_at": now_utc.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "from_date": first_date.isoformat(),
        "through_date": last_date.isoformat(),
        "busy": merged,
    }


