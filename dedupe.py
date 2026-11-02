"""
dedupe.py
Tracks which job IDs have already been seen/notified using Firestore,
so we only email about genuinely new postings.

Firestore collection: "seen_jobs"
Document ID: the normalized job id (e.g. "greenhouse_stripe_123456")
"""

from google.cloud import firestore

COLLECTION_NAME = "seen_jobs"


def get_firestore_client():
    return firestore.Client()


def filter_new_jobs(jobs: list[dict], db=None) -> list[dict]:
    """
    Given a list of normalized job dicts (each with an 'id' key),
    returns only the ones not already recorded in Firestore.
    """
    if db is None:
        db = get_firestore_client()

    new_jobs = []
    collection = db.collection(COLLECTION_NAME)

    for job in jobs:
        doc_ref = collection.document(job["id"])
        if not doc_ref.get().exists:
            new_jobs.append(job)

    return new_jobs


def mark_jobs_as_seen(jobs: list[dict], db=None) -> None:
    """
    Records the given jobs in Firestore so they won't be flagged
    as new again on future runs.
    """
    if db is None:
        db = get_firestore_client()

    collection = db.collection(COLLECTION_NAME)

    for job in jobs:
        collection.document(job["id"]).set({
            "title": job["title"],
            "company": job["company"],
            "source": job["source"],
            "url": job["url"],
            "seen_at": firestore.SERVER_TIMESTAMP,
        })
