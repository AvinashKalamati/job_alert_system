"""Run a shallow live check of every career source in companies.json."""

import json

from fetchers import CONFIGURED_FETCHERS


def _label(argument) -> str:
    if isinstance(argument, str):
        return argument
    return argument.get("company") or argument.get("token") or "unknown"


def _shallow(argument):
    """Limit paginated boards to one page during endpoint verification."""
    if not isinstance(argument, dict):
        return argument
    shallow = dict(argument)
    if "max_pages" in shallow:
        shallow["max_pages"] = 1
    return shallow


def main():
    with open("config/companies.json", "r") as file:
        companies = json.load(file)

    failed = []
    for source, fetcher in CONFIGURED_FETCHERS.items():
        for argument in companies.get(source, []):
            label = _label(argument)
            jobs = fetcher(_shallow(argument))
            if jobs:
                print(f"[OK] {label}: {len(jobs)} job(s) returned by {source}")
            else:
                failed.append(label)
                print(f"[FAILED] {label}: no jobs returned by {source}")

    if failed:
        print("\nUnavailable now: " + ", ".join(failed))
        print("A site may be down, changed, have no openings, or block this IP.")
    else:
        print("\nAll configured career sources returned jobs.")


if __name__ == "__main__":
    main()
