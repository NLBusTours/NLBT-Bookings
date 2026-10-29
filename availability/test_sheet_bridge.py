"""Regression tests: read-only Sheet bridge is opt-in, sanitized and fail-closed."""
import io
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from sync import merge_busy, sheets_busy

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
ENV = {
    "NLBT_SHEETS_BRIDGE_URL": "https://script.google.com/macros/s/test-version/exec",
    "NLBT_SHEETS_BRIDGE_TOKEN": "test-secret-token",
}
VALID = {
    "version": 1,
    "source": "nlbt-inquiries-occupied",
    "timezone": "America/St_Johns",
    "generated_at": "2026-10-29T12:00:00Z",
    "from_date": "2026-10-29",
    "through_date": "2027-12-03",
    "busy": {
        "RT2": {"2026-10-31": [[1260, 1380]]},
        "RX2": {"2026-10-31": [[1350, 1440]], "2026-11-01": [[0, 30]]},
        "R3": {},
    },
}

class SheetBridgeTests(unittest.TestCase):
    def test_unconfigured_bridge_is_not_assumed_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(sheets_busy(NOW, "2026-10-29", "2027-12-03"))

    def test_overlap_union_merges_confirmed_and_calendar(self):
        actual = merge_busy({"2026-10-31": [[1200, 1280]]},
                            {"2026-10-31": [[1260, 1380]]})
        self.assertEqual(actual, {"2026-10-31": [[1200, 1380]]})

    def test_overnight_segments_remain_on_correct_dates(self):
        self.assertEqual(merge_busy({}, VALID["busy"]["RX2"]),
                         VALID["busy"]["RX2"])

    def test_valid_sanitized_feed(self):
        with patch.dict(os.environ, ENV, clear=True):
            with patch("sync.urlopen", return_value=io.BytesIO(json.dumps(VALID).encode())):
                actual = sheets_busy(NOW, "2026-10-29", "2027-12-03")
        self.assertEqual(actual["RT2"]["2026-10-31"], [[1260, 1380]])
        self.assertEqual(set(actual), {"RT2", "RX2", "R3"})

    def test_reject_bad_url_without_contacting_host(self):
        env = {**ENV, "NLBT_SHEETS_BRIDGE_URL":"https://evil.example/macros/s/test/exec"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                sheets_busy(NOW, "2026-10-29", "2027-12-03")

    def test_reject_unsanitized_rows(self):
        bad = {**VALID, "busy": {**VALID["busy"],
                                "RT2": {"2026-10-31": [{"customer_name":"Private"}]}}}
        with patch.dict(os.environ, ENV, clear=True):
            with patch("sync.urlopen", return_value=io.BytesIO(json.dumps(bad).encode())):
                with self.assertRaises(ValueError):
                    sheets_busy(NOW, "2026-10-29", "2027-12-03")

    def test_reject_stale_feed(self):
        stale = {**VALID, "generated_at":"2026-10-20T12:00:00Z"}
        with patch.dict(os.environ, ENV, clear=True):
            with patch("sync.urlopen", return_value=io.BytesIO(json.dumps(stale).encode())):
                with self.assertRaises(ValueError):
                    sheets_busy(NOW, "2026-10-29", "2027-12-03")

if __name__ == "__main__":
    unittest.main()
