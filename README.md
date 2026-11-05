# Job Alert System

Checks configured company career pages every 30 minutes
for new entry-level / new-grad software engineering roles, then emails and
texts you when a new match is found.

## How it works

1. `fetchers.py` pulls current job listings from each configured public
   career feed or careers page and converts them to one common format.
2. `filters.py` keeps only postings matching new-grad/SDE1/SDE2 style
   keywords, excluding senior/staff/lead roles.
3. `dedupe.py` checks Firestore to see which of those postings are new
   (not previously seen).
4. `mailer.py` emails the full list via Gmail SMTP.
5. `sms.py` sends one concise Twilio SMS with the first match and total count.
6. `main.py` ties it all together as a Cloud Function entry point.

## Configured CSV companies

The first 20 rows of `h1b-102-companies-careers-pages.csv` are configured,
plus Oracle, PayPal, Adobe, ServiceNow, Uber, Apple, Palo Alto Networks, eBay,
and DoorDash.
Highspot's careers page redirects to Seismic.

Large boards are scanned newest-first with page limits set in
`config/companies.json`. This makes a 30-minute alert run practical while still
catching newly published jobs. Tesla may reject requests from some cloud IPs;
that failure is isolated and does not stop the other companies.

## Step 1 — Verify company tokens

Career sites sometimes change their endpoints. Before deploying:

```bash
pip install -r requirements.txt
python verify_endpoints.py
```

This performs a shallow live check of every configured source. For any FAILED one:

1. Open that company's real careers page in your browser
2. Open DevTools (F12) → Network tab → filter "Fetch/XHR" → reload the page
3. Find the request returning the job list JSON, copy its token/slug
4. Update `config/companies.json` with the correct token
5. Re-run `verify_endpoints.py` until everything shows OK

## Step 2 — Set up Gmail App Password

1. Go to your Google Account → Security → enable 2-Step Verification (if not already on)
2. Go to https://myaccount.google.com/apppasswords
3. Generate an App Password for "Mail"
4. Save the 16-character password — you'll use it as `GMAIL_APP_PASSWORD`

## Step 3 — Set up Twilio SMS

Before deploying, create a Twilio account and obtain a Twilio phone number.
Copy the Account SID and Auth Token from the Twilio Console. The destination
number must be verified first when using a Twilio trial account. Phone numbers
must use E.164 format, such as `+15551234567`.

The SMS integration uses these environment variables:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` — your Twilio number
- `NOTIFY_TO_PHONE` — your destination number

## Step 4 — Set up Google Cloud

```bash
# Install gcloud CLI if you haven't: https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable firestore.googleapis.com

# Create a Firestore database (Native mode) if you don't have one
gcloud firestore databases create --location=us-central1
```

## Step 5 — Deploy the Cloud Function

From inside the `job-alert-system/` directory:

```bash
gcloud functions deploy job-alert-check \
  --runtime python312 \
  --trigger-http \
  --entry-point job_check_http \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GMAIL_ADDRESS=your_email@gmail.com,GMAIL_APP_PASSWORD=your_16_char_app_password,NOTIFY_TO_EMAIL=your_email@gmail.com,TWILIO_ACCOUNT_SID=your_account_sid,TWILIO_AUTH_TOKEN=your_auth_token,TWILIO_FROM_NUMBER=+15550000001,NOTIFY_TO_PHONE=+15550000002
```

Note: `--allow-unauthenticated` is fine here since the function has no
sensitive input and just runs a fixed check — but if you'd rather lock it
down, remove that flag and instead have Cloud Scheduler authenticate via
an OIDC token (I can walk you through that if you want the extra step).

After deploying, note the **Trigger URL** it gives you — you'll need it
for the next step.

## Step 6 — Schedule it every 30 minutes

```bash
gcloud scheduler jobs create http job-alert-schedule \
  --schedule="*/30 * * * *" \
  --uri="YOUR_CLOUD_FUNCTION_TRIGGER_URL" \
  --http-method=GET \
  --location=us-central1
```

That's it — Cloud Scheduler will now hit your function every 30 minutes,
which checks all companies and sends email plus SMS when something new and
relevant shows up.

## Step 7 — Test it locally first (recommended before deploying)

```bash
pip install -r requirements.txt
export GMAIL_ADDRESS=your_email@gmail.com
export GMAIL_APP_PASSWORD=your_16_char_app_password
export NOTIFY_TO_EMAIL=your_email@gmail.com
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token
export TWILIO_FROM_NUMBER=+15550000001
export NOTIFY_TO_PHONE=+15550000002
export GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

python main.py
```

This runs one check locally and prints what it found, so you can confirm
everything works before deploying.

Run the fetcher unit tests without sending email or touching Firestore:

```bash
python -m unittest discover -s tests -v
```

## Optional outbound proxy

The fetchers work normally without a proxy. To route their traffic through one
HTTP/HTTPS forward proxy, put one of these settings in the protected systemd
environment file (`/etc/job-alert-system.env` in the server setup):

```ini
JOB_ALERT_PROXY_URL=http://USERNAME:PASSWORD@HOST:PORT
```

Alternatively, place `{"proxy_url": "..."}` in a mode-600 JSON file readable
only by the systemd service user and set `JOB_ALERT_PROXY_FILE` to its path.
Do not commit either secret.
Test the configured proxy without contacting any careers site:

```bash
python proxy.py
```

Outbound concurrency defaults to 10 total fetcher workers and 2 requests per
domain. Override them only when your network and the source's published limits
permit it:

```ini
JOB_ALERT_MAX_WORKERS=10
JOB_ALERT_PER_DOMAIN_CONCURRENCY=2
```

The application does not rotate proxies in response to rate limits or access
blocks. To roll back proxy use, remove the proxy setting and restart the next
systemd run; no code or Firestore changes are needed.

## Adding Phase 2 companies later

Greenhouse and Lever companies only need a token added to
`config/companies.json`. Other career systems can reuse the configured adapters
in `fetchers.py`; add another adapter only when the company uses a new system.

## Adjusting keywords

Edit `config/keywords.json` any time — include/exclude lists are
plain lists of lowercase substrings checked against job titles.

## Costs

At 30-min intervals (48 runs/day), this comfortably stays within:
- Cloud Functions free tier (2M invocations/month free)
- Cloud Scheduler free tier (3 free jobs)
- Firestore free tier (50K reads, 20K writes/day free)

The Google Cloud portion should usually remain within its free tiers. Twilio
phone-number and per-message charges may apply; the code sends at most one
concise SMS per job-check run with new matches.
