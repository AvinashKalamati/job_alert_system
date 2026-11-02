import unittest
import sys
from types import ModuleType
from unittest.mock import patch


# main imports the production Firestore adapter, whose package is installed in
# Cloud Functions but is intentionally not needed for this orchestration test.
dedupe_stub = ModuleType("dedupe")
dedupe_stub.filter_new_jobs = lambda jobs: jobs
dedupe_stub.mark_jobs_as_seen = lambda jobs: None
with patch.dict(sys.modules, {"dedupe": dedupe_stub}):
    import main


class MainTests(unittest.TestCase):
    @patch.object(main, "mark_jobs_as_seen")
    @patch.object(main, "send_job_alert_sms")
    @patch.object(main, "send_job_alert_email")
    @patch.object(main, "filter_new_jobs")
    @patch.object(main, "filter_jobs")
    @patch.object(main, "fetch_all_jobs")
    @patch.object(main, "load_keywords")
    @patch.object(main, "load_companies")
    def test_new_jobs_trigger_email_sms_and_dedupe(
        self,
        load_companies,
        load_keywords,
        fetch_all_jobs,
        filter_jobs,
        filter_new_jobs,
        send_email,
        send_sms,
        mark_seen,
    ):
        job = {
            "id": "source_company_1",
            "title": "Software Engineer I",
            "company": "Company",
            "source": "source",
            "location": "Remote",
            "url": "https://example.com/job/1",
        }
        load_companies.return_value = {}
        load_keywords.return_value = {}
        fetch_all_jobs.return_value = [job]
        filter_jobs.return_value = [job]
        filter_new_jobs.return_value = [job]

        result = main.run_job_check()

        send_email.assert_called_once_with([job])
        send_sms.assert_called_once_with([job])
        mark_seen.assert_called_once_with([job])
        self.assertIn("found 1 new matches", result)


if __name__ == "__main__":
    unittest.main()
