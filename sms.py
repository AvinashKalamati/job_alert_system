"""Send concise job-alert text messages through Twilio."""

import os

import requests


TWILIO_MESSAGES_URL = (
    "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
)
REQUEST_TIMEOUT = 15
MAX_SMS_LENGTH = 320
REQUIRED_ENV_VARS = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "NOTIFY_TO_PHONE",
)


def build_sms_body(new_jobs: list[dict]) -> str:
    """Build one short alert; the existing email contains the complete list."""
    first = new_jobs[0]
    count = len(new_jobs)
    header = f"Job alert: {count} new match{'es' if count != 1 else ''}.\n"
    suffix = f"\n+{count - 1} more in email." if count > 1 else ""
    url = first.get("url", "")
    company_and_title = f"{first.get('company', 'Unknown')}: {first.get('title', '')}"

    reserved = len(header) + len(url) + len(suffix) + 1
    available = MAX_SMS_LENGTH - reserved
    if available >= 20:
        if len(company_and_title) > available:
            company_and_title = company_and_title[: available - 3].rstrip() + "..."
        return f"{header}{company_and_title}\n{url}{suffix}"

    # Preserve a readable alert if a career site returns an unusually long URL.
    fallback = f"{header}{company_and_title}\nSee email for details.{suffix}"
    return fallback[:MAX_SMS_LENGTH]


def send_job_alert_sms(new_jobs: list[dict]) -> bool:
    """Send one Twilio SMS. Returns False when skipped or delivery fails."""
    if not new_jobs:
        return False

    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"[sms] skipped; missing environment variables: {', '.join(missing)}")
        return False

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    to_number = os.environ["NOTIFY_TO_PHONE"]

    try:
        response = requests.post(
            TWILIO_MESSAGES_URL.format(account_sid=account_sid),
            data={
                "From": from_number,
                "To": to_number,
                "Body": build_sms_body(new_jobs),
            },
            auth=(account_sid, auth_token),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        # Email is the primary complete alert. A transient SMS failure should
        # not cause the same email to be sent again during the next run.
        print(f"[sms] delivery failed: {error}")
        return False

    print(f"Sent SMS for {len(new_jobs)} new job(s) to {to_number}")
    return True
