import json
import unittest
from unittest.mock import patch

import fetchers


class FakeResponse:
    def __init__(self, json_data=None, text="", headers=None, content=None):
        self._json_data = json_data
        self.text = text
        self.content = content if content is not None else text.encode()
        self.headers = headers or {}

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
    def test_netflix_classic_eightfold(self, get):
        get.return_value = FakeResponse({"positions": [{
            "id": "N1", "name": "Software Engineer",
            "canonicalPositionUrl": "/careers/job/N1",
            "locations": ["Los Gatos, CA"],
        }], "count": 1})
        jobs = fetchers.fetch_eightfold_jobs({
            "company": "Netflix", "host": "https://explore.jobs.netflix.net",
            "domain": "netflix.com", "api_path": "/api/apply/v2/jobs",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "eightfold_netflix_N1")
        self.assertIn("/api/apply/v2/jobs", get.call_args.args[0])

    @patch("fetchers.requests.get")
    def test_amd_jibe_jobs(self, get):
        get.return_value = FakeResponse({"totalCount": 1, "jobs": [{"data": {
            "req_id": "95813", "slug": "95813", "title": "Software Engineer",
            "city": "Santa Clara", "state": "California", "country": "United States",
        }}]})
        jobs = fetchers.fetch_amd_jobs({"company": "AMD", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "amd_amd_95813")
        self.assertEqual(jobs[0]["location"], "Santa Clara, California, United States")

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
    def test_ibm(self, post):
        post.return_value = FakeResponse({"hits": {"total": {"value": 1}, "hits": [{
            "_id": "document-id",
            "_source": {
                "title": "Entry Level Software Developer",
                "url": "https://www.ibm.com/careers/search?jobId=12345",
                "field_keyword_19": "Austin, TX",
            },
        }]}})
        jobs = fetchers.fetch_ibm_jobs({"company": "IBM", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "ibm_ibm_12345")
        self.assertEqual(jobs[0]["location"], "Austin, TX")

    @patch("fetchers.requests.get")
    def test_smartrecruiters(self, get):
        get.return_value = FakeResponse({
            "totalFound": 1,
            "content": [{
                "id": "123",
                "name": "Software Engineer",
                "location": {"city": "Santa Clara", "country": "US"},
            }],
        })
        jobs = fetchers.fetch_smartrecruiters_jobs({
            "company": "ServiceNow", "identifier": "ServiceNow", "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "smartrecruiters_servicenow_123")
        self.assertEqual(jobs[0]["location"], "Santa Clara, US")

    @patch("fetchers.requests.get")
    def test_oracle_recruiting(self, get):
        get.return_value = FakeResponse({"items": [{
            "TotalJobsCount": 1,
            "requisitionList": [{
                "Id": "456",
                "Title": "Software Developer I",
                "PrimaryLocation": "Austin, TX",
            }],
        }]})
        jobs = fetchers.fetch_oracle_recruiting_jobs({
            "company": "Oracle",
            "host": "https://example.oraclecloud.com",
            "site": "CX_1",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "oracle_recruiting_oracle_456")
        self.assertIn("/sites/CX_1/job/456", jobs[0]["url"])

    @patch("fetchers.requests.Session")
    def test_apple(self, session_factory):
        session = session_factory.return_value.__enter__.return_value
        session.get.return_value = FakeResponse(headers={
            "x-apple-csrf-token": "csrf-token",
        })
        session.post.return_value = FakeResponse({"res": {
            "totalRecords": 1,
            "searchResults": [{
                "positionId": "200123456-0001",
                "postingTitle": "Software Engineer",
                "transformedPostingTitle": "software-engineer",
                "locations": [{"name": "Cupertino, CA"}],
            }],
        }})
        jobs = fetchers.fetch_apple_jobs({"company": "Apple", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "apple_apple_200123456-0001")
        self.assertEqual(jobs[0]["location"], "Cupertino, CA")
        self.assertEqual(
            session.post.call_args.kwargs["headers"]["X-Apple-CSRF-Token"],
            "csrf-token",
        )

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

    @patch("fetchers.requests.post")
    def test_vmware_workday_searches_broadcom_board(self, post):
        post.return_value = FakeResponse({"total": 1, "jobPostings": [{
            "title": "VMware Engineer",
            "externalPath": "/job/Remote/VMware-Engineer_R123",
            "locationsText": "Remote",
            "bulletFields": ["R123"],
        }]})
        jobs = fetchers.fetch_workday_jobs({
            "company": "VMware",
            "host": "https://broadcom.wd1.myworkdayjobs.com",
            "tenant": "broadcom",
            "site": "External_Career",
            "search_text": "VMware",
            "max_pages": 1,
        })
        self.assertEqual(post.call_args.kwargs["json"]["searchText"], "VMware")
        self.assertEqual(jobs[0]["company"], "VMware")

    @patch("fetchers.time.sleep")
    @patch("fetchers.requests.post")
    def test_workday_retries_rate_limit(self, post, sleep):
        limited = FakeResponse()
        limited.status_code = 429
        success = FakeResponse({"total": 0, "jobPostings": []})
        success.status_code = 200
        post.side_effect = [limited, success]
        fetchers.fetch_workday_jobs({
            "company": "Broadcom",
            "host": "https://broadcom.wd1.myworkdayjobs.com",
            "tenant": "broadcom", "site": "External_Career", "max_pages": 1,
        })
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.5)

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

    @patch("fetchers.requests.get")
    def test_atlassian_embedded_jobs(self, get):
        get.return_value = FakeResponse(text="""
          <script>window._uniformPreloadedComposition={
            "content": [{"fields": {
              "id": "123", "title": "Software Engineer",
              "applyUrl": "https://careers-americas.icims.com/jobs/123",
              "locations": ["Remote"]
            }}]};</script>
        """)
        jobs = fetchers.fetch_atlassian_jobs({
            "company": "Atlassian", "url": "https://example.com/jobs"
        })
        self.assertEqual(jobs[0]["id"], "atlassian_atlassian_123")
        self.assertEqual(jobs[0]["location"], "Remote")

    @patch("fetchers.requests.get")
    def test_expedia_jobs_sitemap(self, get):
        get.return_value = FakeResponse(text="""<?xml version="1.0"?>
          <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://careers.expediagroup.com/job/software-development-engineer-ii/seattle-wa/R-123/</loc></url>
          </urlset>
        """)
        jobs = fetchers.fetch_expedia_jobs({
            "company": "Expedia",
            "sitemap_url": "https://careers.expediagroup.com/jobs-sitemap.xml",
        })
        self.assertEqual(jobs[0]["id"], "expedia_expedia_R-123")
        self.assertEqual(jobs[0]["title"], "software development engineer ii")
        self.assertEqual(jobs[0]["location"], "seattle wa")
        self.assertTrue(jobs[0]["url"].startswith("https://"))

    @patch("fetchers.requests.get")
    def test_talentbrew_job_card(self, get):
        get.return_value = FakeResponse(text="""
          <section id="search-results-list"><ul><li>
            <a href="/job/seattle/software-engineer/45483/123" data-job-id="123">
              <h2>Software Engineer</h2><span class="job-location">Seattle, WA</span>
            </a>
          </li></ul></section>
          <input class="pagination-current" max="1" value="1">
        """)
        jobs = fetchers.fetch_talentbrew_jobs({
            "company": "Comcast / NBCUniversal",
            "url": "https://jobs.comcast.com/search-jobs", "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "talentbrew_comcast_nbcuniversal_123")
        self.assertEqual(jobs[0]["location"], "Seattle, WA")

    @patch("fetchers.requests.get")
    def test_netapp_talentbrew_h3_title_excludes_location(self, get):
        get.return_value = FakeResponse(text="""
          <ul><li><a href="/job/example/456" data-job-id="456">
            <h3>Software Engineer</h3>
            <span class="job-location">San Jose, CA</span>
          </a></li></ul>
        """)
        jobs = fetchers.fetch_talentbrew_jobs({
            "company": "NetApp", "url": "https://careers.netapp.com/search-jobs",
            "max_pages": 1,
        })
        self.assertEqual(jobs[0]["title"], "Software Engineer")

    @patch("fetchers.requests.post")
    def test_snap_workday_multiple_locations_uses_path(self, post):
        post.return_value = FakeResponse({"total": 1, "jobPostings": [{
            "title": "Software Engineer",
            "externalPath": "/job/New-York-New-York/Software-Engineer_R1",
            "locationsText": "2 Locations", "bulletFields": ["R1"],
        }]})
        jobs = fetchers.fetch_workday_jobs({
            "company": "Snap", "host": "https://snapchat.wd1.myworkdayjobs.com",
            "tenant": "snapchat", "site": "snap", "max_pages": 1,
        })
        self.assertEqual(jobs[0]["id"], "workday_snap_R1")
        self.assertEqual(jobs[0]["location"], "New York New York")

    @patch("fetchers.requests.get")
    def test_linkedin_guest_jobs(self, get):
        get.return_value = FakeResponse(text="""
          <li><div class="base-search-card" data-entity-urn="urn:li:jobPosting:123">
          <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/test-123?tracking=1"></a>
          <h3 class="base-search-card__title">Software Engineer</h3>
          <span class="job-search-card__location">Sunnyvale, CA</span>
          </div></li>
        """)
        jobs = fetchers.fetch_linkedin_jobs({
            "company": "LinkedIn", "company_id": 1337, "max_pages": 1,
        })
        self.assertEqual(jobs[0]["url"], "https://www.linkedin.com/jobs/view/test-123")

    @patch("fetchers.requests.get")
    def test_sap_legacy_search(self, get):
        get.return_value = FakeResponse(text="""
          <table><tr class="data-row"><td class="colTitle">
          <span class="jobTitle hidden-phone"><a class="jobTitle-link"
          href="/job/Seattle-Software-Engineer/123/">Software Engineer</a></span></td>
          <td class="colLocation"><span class="jobLocation">Seattle, WA</span></td>
          </tr></table>
        """)
        jobs = fetchers.fetch_sap_jobs({"company": "SAP America", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "sap_sap_america_123")
        self.assertEqual(jobs[0]["location"], "Seattle, WA")

    @patch("fetchers.requests.get")
    def test_nutanix_jobvite(self, get):
        get.return_value = FakeResponse(text="""
          <table class="jv-job-list"><tbody><tr>
          <td class="jv-job-list-name"><a href="/nutanix/job/o123">Software Engineer</a></td>
          <td class="jv-job-list-location">San Jose, California</td>
          </tr></tbody></table>
        """)
        jobs = fetchers.fetch_jobvite_jobs({
            "company": "Nutanix", "url": "https://jobs.jobvite.com/nutanix/jobs",
        })
        self.assertEqual(jobs[0]["id"], "jobvite_nutanix_o123")

    @patch("fetchers.requests.get")
    def test_ea_results_extract_location_and_id(self, get):
        get.return_value = FakeResponse(text="""
          <div class="article__header__text">
            <a class="link_result" href="https://jobs.ea.com/en_US/careers/JobDetail/Engineer/123">Engineer</a>
            <span class="list-item-location">Los Angeles, CA</span>
          </div>
        """)
        jobs = fetchers.fetch_ea_jobs({"company": "Electronic Arts", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "ea_electronic_arts_123")
        self.assertEqual(jobs[0]["location"], "Los Angeles, CA")

    @patch("fetchers.requests.get")
    def test_shopify_embedded_posting(self, get):
        get.return_value = FakeResponse(text="""
          <a href="/careers/software-engineer_abc" data-component-extra-job-posting-id="abc">
            <h3>Software Engineer</h3><p id="role-location">Remote - Americas</p>
          </a>
        """)
        jobs = fetchers.fetch_shopify_jobs({"company": "Shopify"})
        self.assertEqual(jobs[0]["id"], "shopify_shopify_abc")
        self.assertEqual(jobs[0]["location"], "Remote - Americas")
        self.assertEqual(get.call_args.args[0], "https://www.shopify.com/careers/jobs")

    @patch("fetchers.requests.get")
    def test_zoom_feed_uses_public_job_page(self, get):
        get.return_value = FakeResponse([{ "data": {
            "referenceNumber": "R1", "jobName": "Software Engineer",
            "fullAddress": "San Jose, United States of America",
            "jobURL": "https://careers.zoom.us/job-details/software-engineer",
            "activeStatus": True,
        }}])
        jobs = fetchers.fetch_zoom_jobs({"company": "Zoom"})
        self.assertEqual(jobs[0]["id"], "zoom_zoom_R1")
        self.assertIn("www.careers.zoom.us", jobs[0]["url"])

    @patch("fetchers.requests.get")
    def test_disney_embedded_search_results(self, get):
        payload = {"eagerLoadRefineSearch": {"totalHits": 1, "data": {
            "jobs": [{"jobId": "123", "title": "Engineer",
                      "location": "Burbank, California, United States"}],
        }}}
        get.return_value = FakeResponse(
            text=f"<script>phApp.ddo = {json.dumps(payload)};</script>"
        )
        jobs = fetchers.fetch_disney_jobs({"company": "Disney", "max_pages": 1})
        self.assertEqual(jobs[0]["id"], "disney_disney_123")
        self.assertEqual(jobs[0]["location"], "Burbank, California, United States")

    @patch("fetchers.requests.post")
    def test_confluent_ibm_search_uses_keyword(self, post):
        post.return_value = FakeResponse({"hits": {"total": {"value": 1}, "hits": [{
            "_id": "abc", "_source": {"title": "Engineer - Confluent",
            "url": "https://careers.ibm.com/careers/JobDetail?jobId=123",
            "field_keyword_19": "San Jose, CA"},
        }]}})
        jobs = fetchers.fetch_ibm_jobs({"company": "Confluent", "search_text": "Confluent", "max_pages": 1})
        self.assertEqual(post.call_args.kwargs["json"]["sm"]["query"], "Confluent")
        self.assertEqual(jobs[0]["company"], "Confluent")


if __name__ == "__main__":
    unittest.main()
