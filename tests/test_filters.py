import unittest

from filters import is_relevant_job


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


if __name__ == "__main__":
    unittest.main()
