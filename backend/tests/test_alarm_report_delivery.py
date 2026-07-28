"""Alarm report webhook delivery tests."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.infrastructure.reports.alarm_report import AlarmReportResult, deliver_alarm_report_webhook


class FakeResponse:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class AlarmReportDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.previous_url = os.environ.get("ALARM_REPORT_WEBHOOK_URL")
        self.previous_token = os.environ.get("ALARM_REPORT_WEBHOOK_TOKEN")
        self.tmp = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.tmp.name) / "alarm-report.csv"
        self.summary_path = Path(self.tmp.name) / "alarm-report.json"
        self.csv_path.write_text("alarm_id\n1\n", encoding="utf-8")
        self.summary_path.write_text(json.dumps({"total_count": 1}), encoding="utf-8")
        self.result = AlarmReportResult(
            csv_path=self.csv_path,
            summary_path=self.summary_path,
            total_count=1,
            removed_files=[],
        )

    def tearDown(self):
        if self.previous_url is None:
            os.environ.pop("ALARM_REPORT_WEBHOOK_URL", None)
        else:
            os.environ["ALARM_REPORT_WEBHOOK_URL"] = self.previous_url
        if self.previous_token is None:
            os.environ.pop("ALARM_REPORT_WEBHOOK_TOKEN", None)
        else:
            os.environ["ALARM_REPORT_WEBHOOK_TOKEN"] = self.previous_token
        self.tmp.cleanup()

    def test_delivery_skips_when_webhook_url_missing(self):
        os.environ.pop("ALARM_REPORT_WEBHOOK_URL", None)

        delivery = deliver_alarm_report_webhook(self.result)

        self.assertFalse(delivery.delivered)
        self.assertIsNone(delivery.url)

    def test_delivery_rejects_non_https_url(self):
        delivery = deliver_alarm_report_webhook(self.result, webhook_url="http://siem.local/report")

        self.assertFalse(delivery.delivered)
        self.assertEqual(delivery.url, "http://siem.local/report")
        self.assertIn("HTTPS", delivery.message)

    def test_delivery_posts_summary_and_hashes_to_https_webhook(self):
        captured = {}

        def fake_opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        delivery = deliver_alarm_report_webhook(
            self.result,
            webhook_url="https://siem.example.test/alarm-report",
            token="secret-token",
            timeout_seconds=7,
            opener=fake_opener,
        )

        self.assertTrue(delivery.delivered)
        self.assertEqual(delivery.status_code, 202)
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(captured["body"]["event"], "alarm_report.generated")
        self.assertEqual(captured["body"]["total_count"], 1)
        self.assertEqual(len(captured["body"]["artifacts"]["csv"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
