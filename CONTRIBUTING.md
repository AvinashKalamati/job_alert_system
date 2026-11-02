# Contributing

## Getting Started

Use Python 3.12, create a virtual environment, and install the pinned
dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Making Changes

Keep changes narrowly focused. Add or update unit tests in `tests/` for every
behavior change. Do not commit credentials, phone numbers, service-account
keys, or `.env` files. Run the offline suite before opening a pull request:

```bash
python -m unittest discover -s tests -v
```

Use concise, imperative commit subjects, for example: `Add Greenhouse retry`.
Describe the change, tests run, and any configuration or deployment impact in
the pull request. Use `python verify_endpoints.py` only when changing live
career-source configuration or adapters.
