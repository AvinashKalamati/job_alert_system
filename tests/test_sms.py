import os
import unittest
from unittest.mock import Mock, patch

from sms import MAX_SMS_LENGTH, build_sms_body, send_job_alert_sms


JOBS = [
    {
        "title": "Software Engineer I",
        "company": "Amazon",
        "location": "Seattle, WA",
        "url": "https://example.com/jobs/1",
    },
    {
        "title": "University Graduate Software Engineer",
        "company": "Google",
        "location": "Mountain View, CA",
        "url": "https://example.com/jobs/2",
    },
]


class SmsTests(unittest.TestCase):
    def test_body_is_concise_and_mentions_additional_jobs(self):
        body = build_sms_body(JOBS)
        self.assertLessEqual(len(body), MAX_SMS_LENGTH)
        self.assertIn("Amazon: Software Engineer I", body)
        self.assertIn("+1 more in email", body)

    @patch("sms.requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_configuration_skips_sms(self, post):
        self.assertFalse(send_job_alert_sms(JOBS))
        post.assert_not_called()

    @patch("sms.requests.post")
    @patch.dict(
        os.environ,
        {
            "TWILIO_ACCOUNT_SID": "AC123",
            "TWILIO_AUTH_TOKEN": "secret",
            "TWILIO_FROM_NUMBER": "+15550000001",
            "NOTIFY_TO_PHONE": "+15550000002",
        },
        clear=True,
    )
    def test_sends_through_twilio_messages_api(self, post):
        post.return_value = Mock()

        self.assertTrue(send_job_alert_sms(JOBS))

        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(
            args[0],
            "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json",
        )
        self.assertEqual(kwargs["auth"], ("AC123", "secret"))
        self.assertEqual(kwargs["data"]["From"], "+15550000001")
        self.assertEqual(kwargs["data"]["To"], "+15550000002")


if __name__ == "__main__":
    unittest.main()
