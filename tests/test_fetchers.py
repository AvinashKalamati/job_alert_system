import unittest
from unittest.mock import patch

import fetchers


class FakeResponse:
    def __init__(self, json_data=None, text=""):
        self._json_data = json_data
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


class FetcherTests(unittest.TestCase):
    @patch("fetchers.requests.get")
    def test_amazon(self, get):
        get.return_value = FakeResponse(
            {"jobs": [{
                "id_icims": "A1",
                "title": "Software Engineer I",
                "job_path": "/en/jobs/A1/test",
                "normalized_location": "US, WA, Seattle",
            }]}
        )
        jobs = fetchers.fetch_amazon_jobs({"company": "Amazon", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "amazon_amazon_A1")
        self.assertEqual(jobs[0]["url"], "https://www.amazon.jobs/en/jobs/A1/test")

    @patch("fetchers.requests.get")
    def test_microsoft_eightfold(self, get):
        get.return_value = FakeResponse({"data": {"positions": [{
            "id": "M1",
            "name": "Software Engineer",
            "canonicalPositionUrl": "/careers/job/M1",
            "locations": ["Redmond, WA"],
        }], "count": 1}})
        jobs = fetchers.fetch_eightfold_jobs({
            "company": "Microsoft",
            "host": "https://apply.careers.microsoft.com",
            "domain": "microsoft.com",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["company"], "Microsoft")
        self.assertEqual(jobs[0]["location"], "Redmond, WA")

    @patch("fetchers.requests.get")
    def test_google_html(self, get):
        get.return_value = FakeResponse(text="""
            <div class="sMn82b">
              <a href="jobs/results/123-software-engineer"><h3 class="QJPWVe">Software Engineer</h3></a>
              <span class="r0wTof">Mountain View, CA</span>
            </div>
        """)
        jobs = fetchers.fetch_google_jobs({"company": "Google", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "google_google_123")
        self.assertIn("/jobs/results/123-software-engineer", jobs[0]["url"])

    @patch("fetchers.requests.post")
    def test_bytedance(self, post):
        post.return_value = FakeResponse({"code": 0, "data": {
            "count": 1,
            "job_post_list": [{
                "id": "B1",
                "title": "Graduate Software Engineer",
                "city_info": {"en_name": "San Jose"},
            }],
        }})
        jobs = fetchers.fetch_bytedance_jobs({
            "company": "TikTok / ByteDance", "max_pages": 1
        })
        self.assertEqual(jobs[0]["location"], "San Jose")
        self.assertIn("/position/B1/detail", jobs[0]["url"])

    @patch("fetchers.requests.get")
    def test_tesla(self, get):
        get.return_value = FakeResponse({"response": {
            "listings": [{
                "id": "T1",
                "t": "Software Engineer",
                "l": "10",
            }],
            "lookup": {"locations": {"10": "Austin, TX"}},
        }})
        jobs = fetchers.fetch_tesla_jobs({"company": "Tesla"})
        self.assertEqual(jobs[0]["id"], "tesla_tesla_T1")
        self.assertEqual(jobs[0]["title"], "Software Engineer")
        self.assertEqual(jobs[0]["location"], "Austin, TX")
        self.assertTrue(jobs[0]["url"].endswith("/careers/search/job/T1"))

    @patch("fetchers.requests.get")
    def test_remitly_mcloud(self, get):
        get.return_value = FakeResponse({
            "totalHits": 1,
            "searchResults": [{"job": {
                "id": "R1",
                "title": "Software Development Engineer I",
                "url": "https://careers.remitly.com/job/R1",
                "primary_city": "Seattle",
                "primary_state": "Washington",
                "primary_country": "United States",
            }}],
        })
        jobs = fetchers.fetch_mcloud_jobs({
            "company": "Remitly",
            "company_name": "companies/test",
            "filter": "is_internal=\"Remitly_Careers\"",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["company"], "Remitly")
        self.assertEqual(jobs[0]["location"], "Seattle, Washington, United States")

    @patch("fetchers.requests.get")
    def test_smartsheet_greenhouse(self, get):
        get.return_value = FakeResponse({"jobs": [{
            "id": 7,
            "title": "Software Engineer II",
            "absolute_url": "https://job-boards.greenhouse.io/smartsheet/jobs/7",
            "location": {"name": "Remote"},
        }]})
        jobs = fetchers.fetch_greenhouse_jobs("smartsheet")
        self.assertEqual(jobs[0]["id"], "greenhouse_smartsheet_7")

    @patch("fetchers.requests.get")
    def test_snowflake_ashby(self, get):
        get.return_value = FakeResponse({"jobs": [{
            "id": "S1",
            "title": "Software Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/snowflake/S1",
            "location": "San Mateo, CA",
            "isListed": True,
        }]})
        jobs = fetchers.fetch_ashby_jobs({"company": "Snowflake", "token": "snowflake"})
        self.assertEqual(jobs[0]["source"], "ashby")

    @patch("fetchers.requests.post")
    def test_zillow_workday(self, post):
        post.return_value = FakeResponse({
            "total": 1,
            "jobPostings": [{
                "title": "Software Engineer",
                "externalPath": "/job/Remote-USA/Software-Engineer_P123",
                "locationsText": "Remote-USA",
                "bulletFields": ["P123"],
            }],
        })
        jobs = fetchers.fetch_workday_jobs({
            "company": "Zillow",
            "host": "https://zillow.wd5.myworkdayjobs.com",
            "tenant": "zillow",
            "site": "Zillow_Group_External",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "workday_zillow_P123")
        self.assertIn("/Zillow_Group_External/job/", jobs[0]["url"])

    @patch("fetchers.requests.get")
    def test_highspot_seismic(self, get):
        get.return_value = FakeResponse(text="""
          <a href="/careers/job-detail/?jid=2384&amp;pid=1">
            <div class="text-h6">Associate Software Engineer</div>
            <div class="text-body2">Boston, MA</div>
          </a>
        """)
        jobs = fetchers.fetch_seismic_jobs({"company": "Highspot / Seismic"})
        self.assertEqual(jobs[0]["id"], "seismic_highspot_seismic_2384")
        self.assertEqual(jobs[0]["location"], "Boston, MA")


if __name__ == "__main__":
    unittest.main()
