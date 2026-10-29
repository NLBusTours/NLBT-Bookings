"""Regression tests for private bus availability sanitization."""
import unittest
from datetime import datetime, timezone
from parse_ics import normalize_private_url, make_snapshot
from publish_issue import body

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)

def calendar(event=""):
    return ("""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//NLBT//TEST//EN
""" + event + "\nEND:VCALENDAR\n").replace("\n", "\r\n").encode()

def event(uid, start, end):
    return f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{start}
DTEND:{end}
SUMMARY:private customer wedding
DESCRIPTION:private@example.com
END:VEVENT"""

class CalendarTests(unittest.TestCase):
    def test_google_private_ical_url(self):
        self.assertIn("calendar.google.com", normalize_private_url(
            "webcal://calendar.google.com/calendar/ical/demo%40example.com/private-token/basic.ics"))

    def test_band_private_ical_url(self):
        self.assertTrue(normalize_private_url("webcal://api.band.us/ical?token=private").startswith("https://"))

    def test_reject_untrusted_url(self):
        for url in ("http://example.com/calendar.ics","https://evil.example/calendar/ical/fake.ics",
                    "https://api.band.us/elsewhere?token=x"):
            with self.assertRaises(ValueError):
                normalize_private_url(url)

    def test_exact_busy_hours(self):
        snap = make_snapshot(calendar(event("private123","20261107T100000","20261107T130000")),NOW)
        self.assertEqual(snap["busy"]["2026-11-07"], [[600,780]])

    def test_empty_but_valid_calendar(self):
        snap = make_snapshot(calendar(),NOW)
        self.assertEqual(snap["busy"], {})

    def test_overlap_merges_without_metadata(self):
        data=calendar(event("one","20261107T100000","20261107T120000")+"\n"+
                      event("two","20261107T110000","20261107T140000"))
        snap=make_snapshot(data,NOW)
        self.assertEqual(snap["busy"]["2026-11-07"],[[600,840]])
        self.assertNotIn("private@example.com",str(snap))
        self.assertNotIn("private customer wedding",str(snap))

    def test_issue_data_privacy(self):
        sample={"version":1,"timezone":"America/St_Johns",
                "generated_at":"2026-10-29T12:00:00Z","from_date":"2026-10-29",
                "through_date":"2027-12-03",
                "buses":{bus:{"busy":{}} for bus in ("RT2","RX2","R3")},
                "secret_token":"SHOULD_NOT_LEAK", "customer_name":"PRIVATE"}
        result=body(sample)
        self.assertNotIn("SHOULD_NOT_LEAK",result)
        self.assertNotIn("PRIVATE",result)
        for bus in ("RT2","RX2","R3"):self.assertIn('"'+bus+'"',result)

if __name__=="__main__":
    unittest.main()
