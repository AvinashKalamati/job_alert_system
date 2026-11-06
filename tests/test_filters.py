import unittest

from filters import filter_jobs, is_relevant_job, is_us_location


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.keywords = {
            "include_keywords": ["software engineer"],
            "exclude_keywords": ["senior", "staff"],
        }

    def test_plain_software_engineer_is_relevant(self):
        self.assertTrue(
            is_relevant_job("Software Engineer", self.keywords)
        )

    def test_senior_software_engineer_is_excluded(self):
        self.assertFalse(
            is_relevant_job("Senior Software Engineer", self.keywords)
        )

    def test_us_location_formats_are_included(self):
        locations = (
            "Seattle, WA",
            "Austin, Texas",
            "United States",
            "USA",
            "U.S.",
            "US, CA, San Francisco",
            "Remote - US",
            "Remote, United States",
        )
        for location in locations:
            with self.subTest(location=location):
                self.assertTrue(is_us_location(location))

    def test_unqualified_or_non_us_locations_are_excluded(self):
        locations = (
            "Remote",
            "Unknown",
            "Toronto, Canada",
            "Remote - Canada",
            "London, United Kingdom",
        )
        for location in locations:
            with self.subTest(location=location):
                self.assertFalse(is_us_location(location))

    def test_filter_jobs_requires_matching_title_and_us_location(self):
        jobs = [
            {"title": "Software Engineer", "location": "New York, NY"},
            {"title": "Software Engineer", "location": "Remote"},
            {"title": "Senior Software Engineer", "location": "Austin, TX"},
        ]

        self.assertEqual(filter_jobs(jobs, self.keywords), [jobs[0]])


if __name__ == "__main__":
    unittest.main()
