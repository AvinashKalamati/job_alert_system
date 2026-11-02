"""
filters.py
Filters raw job postings down to entry-level / new-grad relevant roles
based on include/exclude keyword lists.
"""

import json


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


def filter_jobs(jobs: list[dict], keywords: dict) -> list[dict]:
    return [job for job in jobs if is_relevant_job(job["title"], keywords)]
