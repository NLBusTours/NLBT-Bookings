"""Publish only anonymized per-bus time intervals to one GitHub issue."""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

REPO = "NLBusTours/NLBT-Bookings"
ISSUE = 1
START = "<!-- NLBT_AVAILABILITY_JSON_START"
END = "NLBT_AVAILABILITY_JSON_END -->"

def body(snapshot: dict) -> str:
    # Whitelist output; NEVER write any private iCal event metadata.
    allowed = {
        "version": snapshot["version"],
        "timezone": snapshot["timezone"],
        "sheet_verified": snapshot.get("sheet_verified") is True,
        "generated_at": snapshot["generated_at"],
        "from_date": snapshot["from_date"],
        "through_date": snapshot["through_date"],
        "buses": {bus: {"busy": snapshot["buses"][bus]["busy"]}
                  for bus in ("RT2", "RX2", "R3")},
    }
    return ("Automated **anonymous** occupied times for the three active NLBT buses. "
            "No client details, event descriptions or private calendar tokens are stored. "
            "Open times are available to request, not guaranteed reservations.\n\n"
            + START + "\n" + json.dumps(allowed, separators=(",", ":"), sort_keys=True)
            + "\n" + END)

if __name__ == "__main__":
    path = Path("availability.json")
    if not path.exists():
        print("No complete snapshot available. Previous record remains unverified.")
        raise SystemExit(0)
    if os.getenv("GITHUB_REPOSITORY") != REPO or not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("GitHub write authorization not configured")
    payload = json.dumps({"body": body(json.loads(path.read_text(encoding="utf-8")))}).encode("utf-8")
    req = Request(
        "https://api.github.com/repos/" + REPO + "/issues/" + str(ISSUE),
        data=payload, method="PATCH",
        headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "NLBTAvailability/1.0"},
    )
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("Could not publish anonymous calendar snapshot")
    print("Anonymous bus availability updated")
