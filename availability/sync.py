"""Create one anonymous busy-time snapshot for RT2, RX2 and R3.

RT2 uses the Google Calendar currently named RT; the original Artie (RT) is retired.
Private calendar URLs live only in GitHub Actions secrets.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from datetime import timedelta
from parse_ics import download_ics, normalize_private_url, make_snapshot

CALENDARS = {
    "RT2": "NLBT_RT2_ICAL_URL",
    "RX2": "NLBT_RX2_ICAL_URL",
    "R3": "NLBT_R3_ICAL_URL",
}


def merge_busy(calendar: dict, sheets: dict) -> dict:
    """Union only sanitized interval arrays. Never expose individual sheet rows."""
    result = {}
    for day in sorted(set(calendar) | set(sheets)):
        intervals = calendar.get(day, []) + sheets.get(day, [])
        combined = []
        for start, end in sorted(intervals):
            if combined and start <= combined[-1][1]:
                combined[-1][1] = max(combined[-1][1], end)
            else:
                combined.append([start, end])
        if combined:
            result[day] = combined
    return result


def sheets_busy(now: datetime, first_date: str, through_date: str) -> dict | None:
    """Read ONLY the independent Apps Script sanitized endpoint over HTTPS.

    Missing or invalid setup never claims that RT2 has been fully checked.
    """
    url = os.getenv("NLBT_SHEETS_BRIDGE_URL", "").strip()
    token = os.getenv("NLBT_SHEETS_BRIDGE_TOKEN", "").strip()
    if not url or not token:
        return None
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "script.google.com"
            or not parsed.path.startswith("/macros/s/")
            or not parsed.path.endswith("/exec")
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Invalid private Sheet bridge URL")
    payload = json.dumps({"token":token}).encode("utf-8")
    request = Request(url, method="POST", data=payload,
                      headers={"Content-Type":"application/json",
                               "User-Agent":"NLBTAvailability/1.0"})
    with urlopen(request, timeout=25) as response:
        body = response.read(750001)
    if len(body) > 750000:
        raise ValueError("Sanitized Sheet feed too large")
    data = json.loads(body)
    if (data.get("version") != 1
        or data.get("source") != "nlbt-inquiries-confirmed"
        or data.get("timezone") != "America/St_Johns"
        or data.get("from_date") > first_date or data.get("through_date") < through_date):
        raise ValueError("Invalid or incomplete Sheet availability feed")
    generated_at = datetime.fromisoformat(data["generated_at"].replace("Z","+00:00"))
    if generated_at.tzinfo is None or abs((now - generated_at).total_seconds()) > 600:
        raise ValueError("Sheet feed was not generated recently")
    busy = data["busy"]
    if not isinstance(busy, dict) or set(busy) != set(CALENDARS):
        raise ValueError("Sheet bus list does not match the active fleet")
    safe = {}
    for bus in CALENDARS:
        raw = busy[bus]
        if not isinstance(raw, dict):
            raise ValueError("Bad Sheet interval map")
        clean = {}
        for day, ranges in raw.items():
            if not isinstance(day, str) or not first_date <= day <= through_date:
                raise ValueError("Bad Sheet date")
            if not isinstance(ranges, list) or len(ranges) > 200:
                raise ValueError("Bad Sheet daily intervals")
            validated = []
            for entry in ranges:
                if (not isinstance(entry,list) or len(entry)!=2
                    or any(type(x) is not int for x in entry)
                    or not 0 <= entry[0] < entry[1] <= 1440):
                    raise ValueError("Bad Sheet time range")
                validated.append(entry)
            clean[day] = validated
        safe[bus] = clean
    return safe


def generate() -> dict:
    missing = [key for key in CALENDARS.values() if not os.environ.get(key)]
    if missing:
        raise RuntimeError("One or more private bus calendar secrets are not configured")
    now = datetime.now(timezone.utc)
    entries = {}
    dates = None
    for bus, secret_name in CALENDARS.items():
        try:
            feed = download_ics(normalize_private_url(os.environ[secret_name]))
            parsed = make_snapshot(feed, now)
        except Exception as exc:
            # Deliberately never print the private feed URL, tokens or booking details.
            raise RuntimeError("Could not securely refresh a bus calendar; no data published") from None
        entries[bus] = {"busy": parsed["busy"]}
        if dates is None:
            dates = parsed

    verified = False
    try:
        source = sheets_busy(now, dates["from_date"], dates["through_date"])
        if source is not None:
            for bus in CALENDARS:
                entries[bus]["busy"] = merge_busy(entries[bus]["busy"], source[bus])
            verified = True
    except Exception:
        # Source is incomplete or unavailable; do not publish a misleading
        # fully verified RT2 schedule. Never log credential/error details.
        print("Sheet supplement not verified; RT2 remains manual confirmation")

    return {
        "version": 1,
        "timezone": "America/St_Johns",
        "sheet_verified": verified,
        "generated_at": dates["generated_at"],
        "from_date": dates["from_date"],
        "through_date": dates["through_date"],
        "buses": entries,
    }

if __name__ == "__main__":
    snapshot = generate()
    Path("availability.json").write_text(
        json.dumps(snapshot, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8"
    )
    print("Three anonymous bus schedules generated successfully")
