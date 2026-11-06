"""
filters.py
Filters raw job postings down to entry-level / new-grad relevant roles
based on include/exclude keyword lists.
"""

import json
import re


US_STATE_NAMES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
)
US_STATE_ABBREVIATIONS = (
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
)


def load_keywords(path: str = "config/keywords.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def is_relevant_job(title: str, keywords: dict) -> bool:
    """
    A job is relevant if its title contains at least one include keyword
    AND does not contain any exclude keyword.
    """
    title_lower = title.lower()

    has_include = any(kw in title_lower for kw in keywords["include_keywords"])
    has_exclude = any(kw in title_lower for kw in keywords["exclude_keywords"])

    return has_include and not has_exclude


def is_us_location(location: str) -> bool:
    """Return whether a normalized job location clearly identifies the US."""
    if not location:
        return False

    location_lower = location.lower()
    if re.search(
        r"(?<![a-z])(?:united states(?: of america)?|u\.s\.a\.?|u\.s\.)(?![a-z])",
        location_lower,
    ):
        return True
    if re.search(r"(?<![A-Za-z])(?:US|USA)(?![A-Za-z])", location):
        return True
    if any(
        re.search(rf"\b{re.escape(state)}\b", location_lower)
        for state in US_STATE_NAMES
    ):
        return True
    return any(
        re.search(rf"(?<![A-Za-z]){state}(?![A-Za-z])", location)
        for state in US_STATE_ABBREVIATIONS
    )


def filter_jobs(jobs: list[dict], keywords: dict) -> list[dict]:
    return [
        job
        for job in jobs
        if is_relevant_job(job["title"], keywords)
        and is_us_location(job.get("location", ""))
    ]
