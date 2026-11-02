"""
main.py
Cloud Function entry point. Triggered on a schedule (via Cloud Scheduler
-> Pub/Sub or HTTP trigger) every 30 minutes.

Flow:
  1. Fetch jobs from all configured company career systems
  2. Filter down to relevant entry-level/new-grad titles
  3. Compare against Firestore to find genuinely new postings
  4. Email the new ones and send a concise SMS alert
  5. Mark them as seen so they aren't emailed again
"""

import json

from fetchers import fetch_all_jobs
from filters import load_keywords, filter_jobs
from dedupe import filter_new_jobs, mark_jobs_as_seen
from mailer import send_job_alert_email
from sms import send_job_alert_sms


def load_companies(path: str = "config/companies.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def run_job_check() -> str:
    companies = load_companies()
    keywords = load_keywords()

    all_jobs = fetch_all_jobs(companies)
    print(f"Fetched {len(all_jobs)} total postings across all companies.")

    relevant_jobs = filter_jobs(all_jobs, keywords)
    print(f"{len(relevant_jobs)} postings match entry-level/new-grad keywords.")

    new_jobs = filter_new_jobs(relevant_jobs)
    print(f"{len(new_jobs)} of those are new (not seen before).")

    if new_jobs:
        send_job_alert_email(new_jobs)
        send_job_alert_sms(new_jobs)
        mark_jobs_as_seen(new_jobs)

    return f"Checked {len(all_jobs)} jobs, found {len(new_jobs)} new matches."


def job_check_http(request):
    """HTTP-triggered entry point (for Cloud Scheduler -> HTTP target)."""
    result = run_job_check()
    return result, 200


if __name__ == "__main__":
    # Allows local testing: python main.py
    print(run_job_check())
