# Repository Guidelines

## Project Structure & Module Organization

This is a Python Cloud Function that checks company career pages and sends job
alerts. `main.py` is the HTTP entry point and coordinates fetching, filtering,
deduplication, and notifications. Keep source modules at the repository root:
`fetchers.py` for career-site adapters, `filters.py` for keyword matching,
`dedupe.py` for Firestore state, and `mailer.py`/`sms.py` for notifications.

Runtime configuration belongs in `config/`: `companies.json` defines sources
and `keywords.json` contains lowercase include/exclude substrings. Put unit
tests in `tests/`, named `test_<module>.py`. `verify_endpoints.py` is the
live, shallow source-health check; do not use it as a unit test.

## Build, Test, and Development Commands

Install pinned dependencies with:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The test command runs the offline `unittest` suite. Run
`python verify_endpoints.py` after modifying company tokens or fetcher
adapters; it makes external requests. With required environment variables and
Google credentials set, `python main.py` executes one local alert cycle.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, and standard-library
`unittest`/`unittest.mock` patterns. Prefer `snake_case` for functions,
variables, and JSON keys; use `UPPER_SNAKE_CASE` for module constants (for
example, `MAX_SMS_LENGTH`). Keep fetchers small, return the shared job shape,
and isolate failure of one external source so other sources still run. No
formatter or linter is configured; match the existing straightforward style.

## Testing Guidelines

Add focused tests for changed behavior and mock HTTP, Firestore, SMTP, and
Twilio interactions. Test names should describe the expected outcome, such as
`test_filters_excluded_title`. Run the full discovery command before proposing
changes. There is no stated coverage threshold; maintain or improve coverage
around affected paths.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so use concise imperative commit
subjects, such as `Add Lever pagination support`. Keep commits scoped. Pull
requests should explain the behavior change, list test commands run, link the
relevant issue when available, and include sample output or screenshots for
user-visible notification changes.

## Security & Configuration

Never commit Gmail, Twilio, Google Cloud credentials, phone numbers, or service
account keys. Use environment variables for secrets and keep configuration
updates limited to public career-source data.
