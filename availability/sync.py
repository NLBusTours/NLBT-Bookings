"""Create one anonymous busy-time snapshot for RT2, RX2 and R3.

RT2 uses the Google Calendar currently named RT; the original Artie (RT) is retired.
Private calendar URLs live only in GitHub Actions secrets.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from parse_ics import download_ics, normalize_private_url, make_snapshot

CALENDARS = {
    "RT2": "NLBT_RT2_ICAL_URL",
    "RX2": "NLBT_RX2_ICAL_URL",
    "R3": "NLBT_R3_ICAL_URL",
}

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
    return {
        "version": 1,
        "timezone": "America/St_Johns",
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
