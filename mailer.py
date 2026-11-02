"""
mailer.py
Sends email notifications via Gmail SMTP using an App Password.

Required environment variables (set these in Cloud Function config,
never hardcode them):
    GMAIL_ADDRESS      - your full Gmail address
    GMAIL_APP_PASSWORD - the 16-character App Password (not your login password)
    NOTIFY_TO_EMAIL    - where alerts should be sent (can be same as GMAIL_ADDRESS)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def build_email_body(new_jobs: list[dict]) -> str:
    lines = [f"Found {len(new_jobs)} new matching role(s):\n"]
    for job in new_jobs:
        lines.append(
            f"- {job['title']} @ {job['company'].title()} "
            f"({job['location']})\n  {job['url']}\n"
        )
    return "\n".join(lines)


def send_job_alert_email(new_jobs: list[dict]) -> None:
    if not new_jobs:
        return  # nothing to send

    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ.get("NOTIFY_TO_EMAIL", gmail_address)

    subject = f"🚨 {len(new_jobs)} New Job Match(es) Found"
    body = build_email_body(new_jobs)

    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, to_email, msg.as_string())

    print(f"Sent email with {len(new_jobs)} new job(s) to {to_email}")
