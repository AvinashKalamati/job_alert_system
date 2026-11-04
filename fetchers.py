"""Fetch and normalize jobs from the configured company career systems."""

from concurrent.futures import ThreadPoolExecutor
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
import requests


GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/{token}?mode=json"
AMAZON_URL = "https://www.amazon.jobs/en/search.json"
EIGHTFOLD_URL = "{host}/api/pcsx/search"
GOOGLE_URL = "https://www.google.com/about/careers/applications/jobs/results/"
BYTEDANCE_URL = "https://jobs.bytedance.com/api/v1/public/supplier/search/job/posts"
TESLA_URL = "https://www.tesla.com/cua-api/apps/careers/state"
MCLOUD_URL = "https://jobsapi-google.m-cloud.io/api/job/search"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"
WORKDAY_URL = "{host}/wday/cxs/{tenant}/{site}/jobs"
IBM_URL = "https://www-api.ibm.com/search/api/v2"
SMARTRECRUITERS_URL = (
    "https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
)
ORACLE_RECRUITING_URL = (
    "{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
)
APPLE_CSRF_URL = "https://jobs.apple.com/api/v1/CSRFToken"
APPLE_SEARCH_URL = "https://jobs.apple.com/api/v1/search"

REQUEST_TIMEOUT = 20
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}


def _company_key(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")


def _job(source, company, raw_id, title, url, location="Unknown") -> dict:
    return {
        "id": f"{source}_{_company_key(company)}_{raw_id}",
        "title": (title or "").strip(),
        "url": url or "",
        "company": company,
        "source": source,
        "location": (location or "Unknown").strip(),
    }


def _location(value) -> str:
    """Flatten the string/list/dict location formats used by job boards."""
    if not value:
        return "Unknown"
    if isinstance(value, str):
        return value.strip() or "Unknown"
    if isinstance(value, list):
        parts = [_location(item) for item in value]
        return "; ".join(part for part in parts if part != "Unknown") or "Unknown"
    if isinstance(value, dict):
        for key in ("name", "displayName", "location", "text", "en_name"):
            if value.get(key):
                return _location(value[key])
        parts = [
            str(value[key]).strip()
            for key in ("city", "state", "country")
            if value.get(key)
        ]
        return ", ".join(parts) or "Unknown"
    return str(value)


def _failed(source: str, company: str, error: Exception) -> list[dict]:
    print(f"[{source}:{company}] fetch failed: {error}")
    return []


def fetch_greenhouse_jobs(company_token: str) -> list[dict]:
    """Fetch one Greenhouse board while preserving existing dedupe IDs."""
    try:
        response = requests.get(
            GREENHOUSE_URL.format(token=company_token), timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    except (requests.RequestException, ValueError, AttributeError) as error:
        return _failed("greenhouse", company_token, error)

    return [
        {
            "id": f"greenhouse_{company_token}_{job.get('id')}",
            "title": job.get("title", ""),
            "url": job.get("absolute_url", ""),
            "company": company_token,
            "source": "greenhouse",
            "location": (job.get("location") or {}).get("name", "Unknown"),
        }
        for job in jobs
    ]


def fetch_lever_jobs(company_token: str) -> list[dict]:
    """Fetch one Lever board while preserving existing dedupe IDs."""
    try:
        response = requests.get(
            LEVER_URL.format(token=company_token), timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        jobs = response.json()
        if not isinstance(jobs, list):
            raise ValueError("unexpected Lever response")
    except (requests.RequestException, ValueError) as error:
        return _failed("lever", company_token, error)

    return [
        {
            "id": f"lever_{company_token}_{job.get('id')}",
            "title": job.get("text", ""),
            "url": job.get("hostedUrl", ""),
            "company": company_token,
            "source": "lever",
            "location": (job.get("categories") or {}).get("location", "Unknown"),
        }
        for job in jobs
    ]


def fetch_amazon_jobs(options: dict) -> list[dict]:
    company = options.get("company", "Amazon")
    page_size = 100
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 5))):
            response = requests.get(
                AMAZON_URL,
                params={
                    "offset": page * page_size,
                    "result_limit": page_size,
                    "sort": "recent",
                    "base_query": "",
                },
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
            for posting in jobs:
                normalized.append(
                    _job(
                        "amazon",
                        company,
                        posting.get("id_icims") or posting.get("id"),
                        posting.get("title"),
                        urljoin(
                            "https://www.amazon.jobs", posting.get("job_path", "")
                        ),
                        _location(
                            posting.get("normalized_location")
                            or posting.get("location")
                        ),
                    )
                )
            if len(jobs) < page_size:
                break
    except (requests.RequestException, ValueError, AttributeError) as error:
        return _failed("amazon", company, error)
    return normalized


def fetch_eightfold_jobs(options: dict) -> list[dict]:
    company = options["company"]
    host = options["host"].rstrip("/")
    page_size = int(options.get("page_size", 10))
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 20))):
            response = requests.get(
                EIGHTFOLD_URL.format(host=host),
                params={
                    "domain": options.get("domain", ""),
                    "start": page * page_size,
                    "num": page_size,
                    "sort_by": "timestamp",
                },
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            payload = body.get("data", body)
            jobs = payload.get("positions", payload.get("jobs", []))
            for posting in jobs:
                raw_id = posting.get("id") or posting.get("positionId")
                posting_url = (
                    posting.get("canonicalPositionUrl")
                    or posting.get("positionUrl")
                    or posting.get("url")
                    or f"{host}/careers/job/{raw_id}"
                )
                normalized.append(
                    _job(
                        "eightfold",
                        company,
                        raw_id,
                        posting.get("name")
                        or posting.get("posting_name")
                        or posting.get("title"),
                        urljoin(f"{host}/", posting_url),
                        _location(
                            posting.get("locations")
                            or posting.get("primaryLocation")
                            or posting.get("location")
                        ),
                    )
                )
            total = payload.get("count") or payload.get("total")
            if len(jobs) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (
        requests.RequestException,
        ValueError,
        AttributeError,
        TypeError,
    ) as error:
        return _failed("eightfold", company, error)
    return normalized


def fetch_google_jobs(options: dict) -> list[dict]:
    company = options.get("company", "Google")
    normalized = []
    seen_ids = set()
    try:
        for page in range(1, int(options.get("max_pages", 10)) + 1):
            response = requests.get(
                GOOGLE_URL,
                params={"hl": "en_US", "sort_by": "date", "page": page},
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select("div.sMn82b")
            added = 0
            for card in cards:
                title = card.select_one("h3.QJPWVe")
                link = card.select_one('a[href*="jobs/results/"]')
                if not title or not link:
                    continue
                href = link.get("href", "")
                match = re.search(r"/results/(\d+)", href)
                if not match or match.group(1) in seen_ids:
                    continue
                raw_id = match.group(1)
                seen_ids.add(raw_id)
                added += 1
                place = card.select_one("span.r0wTof")
                normalized.append(
                    _job(
                        "google",
                        company,
                        raw_id,
                        title.get_text(" ", strip=True),
                        urljoin(
                            "https://www.google.com/about/careers/applications/",
                            href,
                        ),
                        place.get_text(" ", strip=True) if place else "Unknown",
                    )
                )
            if not cards or not added:
                break
    except (requests.RequestException, ValueError, AttributeError) as error:
        return _failed("google", company, error)
    return normalized


def fetch_ibm_jobs(options: dict) -> list[dict]:
    """Fetch IBM's public careers search, which is backed by Elasticsearch."""
    company = options.get("company", "IBM")
    page_size = 100
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 5))):
            response = requests.post(
                IBM_URL,
                json={
                    "appId": "careers",
                    "scopes": ["careers2"],
                    "sm": {"query": "", "lang": "zz"},
                    "size": page_size,
                    "from": page * page_size,
                },
                headers={**BROWSER_HEADERS, "Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            hits = (body.get("hits") or {}).get("hits", [])
            for hit in hits:
                job = hit.get("_source") or {}
                url = job.get("url", "")
                raw_id = parse_qs(urlparse(url).query).get("jobId", [None])[0]
                normalized.append(
                    _job(
                        "ibm",
                        company,
                        raw_id or hit.get("_id"),
                        job.get("title"),
                        url,
                        _location(job.get("field_keyword_19")),
                    )
                )
            total = (body.get("hits") or {}).get("total", {})
            total = total.get("value") if isinstance(total, dict) else total
            if len(hits) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (requests.RequestException, ValueError, AttributeError, TypeError) as error:
        return _failed("ibm", company, error)
    return normalized


def fetch_smartrecruiters_jobs(options: dict) -> list[dict]:
    """Fetch a public SmartRecruiters board."""
    company = options["company"]
    identifier = options["identifier"]
    page_size = 100
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 10))):
            response = requests.get(
                SMARTRECRUITERS_URL.format(identifier=identifier),
                params={"limit": page_size, "offset": page * page_size},
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            postings = body.get("content", [])
            for posting in postings:
                raw_id = posting.get("id") or posting.get("uuid")
                normalized.append(
                    _job(
                        "smartrecruiters",
                        company,
                        raw_id,
                        posting.get("name"),
                        posting.get("postingUrl")
                        or f"https://jobs.smartrecruiters.com/{identifier}/{raw_id}",
                        _location(posting.get("location")),
                    )
                )
            total = body.get("totalFound")
            if len(postings) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (requests.RequestException, ValueError, AttributeError, TypeError) as error:
        return _failed("smartrecruiters", company, error)
    return normalized


def fetch_oracle_recruiting_jobs(options: dict) -> list[dict]:
    """Fetch a public Oracle Recruiting Cloud candidate-experience board."""
    company = options["company"]
    host = options["host"].rstrip("/")
    site = options["site"]
    page_size = 100
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 10))):
            finder = (
                f"findReqs;siteNumber={site},limit={page_size},"
                f"offset={page * page_size},sortBy=POSTING_DATES_DESC"
            )
            response = requests.get(
                ORACLE_RECRUITING_URL.format(host=host),
                params={
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": finder,
                },
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            result = (body.get("items") or [{}])[0]
            postings = result.get("requisitionList") or []
            for posting in postings:
                raw_id = posting.get("Id")
                normalized.append(
                    _job(
                        "oracle_recruiting",
                        company,
                        raw_id,
                        posting.get("Title"),
                        f"{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{raw_id}",
                        posting.get("PrimaryLocation"),
                    )
                )
            total = result.get("TotalJobsCount")
            if len(postings) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (requests.RequestException, ValueError, AttributeError, TypeError) as error:
        return _failed("oracle_recruiting", company, error)
    return normalized


def fetch_apple_jobs(options: dict) -> list[dict]:
    """Fetch Apple's public careers search API using its browser session flow."""
    company = options.get("company", "Apple")
    page_size = 20
    normalized = []
    try:
        with requests.Session() as session:
            token_response = session.get(
                APPLE_CSRF_URL, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT
            )
            token_response.raise_for_status()
            csrf_token = token_response.headers.get("x-apple-csrf-token")
            headers = dict(BROWSER_HEADERS)
            if csrf_token:
                headers["X-Apple-CSRF-Token"] = csrf_token

            for page in range(1, int(options.get("max_pages", 10)) + 1):
                response = session.post(
                    APPLE_SEARCH_URL,
                    json={
                        "query": "",
                        "filters": {},
                        "page": page,
                        "locale": "en-us",
                        "sort": "",
                        "format": {
                            "longDate": "MMMM D, YYYY",
                            "mediumDate": "MMM D, YYYY",
                        },
                    },
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                body = response.json()
                result = body.get("res") or body
                postings = (
                    result.get("searchResults")
                    or result.get("searchResultItems")
                    or result.get("jobs")
                    or []
                )
                for posting in postings:
                    raw_id = posting.get("positionId") or posting.get("reqId")
                    title = posting.get("postingTitle", "")
                    slug = posting.get("transformedPostingTitle") or re.sub(
                        r"[^a-z0-9]+", "-", title.lower()
                    ).strip("-")
                    normalized.append(
                        _job(
                            "apple",
                            company,
                            raw_id,
                            title,
                            f"https://jobs.apple.com/en-us/details/{raw_id}/{slug}",
                            _location(posting.get("locations")),
                        )
                    )
                total = result.get("totalRecords")
                if len(postings) < page_size or (
                    total is not None and len(normalized) >= int(total)
                ):
                    break
    except (requests.RequestException, ValueError, AttributeError, TypeError) as error:
        return _failed("apple", company, error)
    return normalized


def fetch_bytedance_jobs(options: dict) -> list[dict]:
    company = options.get("company", "TikTok / ByteDance")
    page_size = 100
    normalized = []
    headers = {
        **BROWSER_HEADERS,
        "Content-Type": "application/json",
        "accept-language": "en-US",
        "website-path": "en",
        "x-tt-env": "boe_epam_api",
        "Origin": "https://joinbytedance.com",
        "Referer": "https://joinbytedance.com/search",
    }
    try:
        for page in range(int(options.get("max_pages", 20))):
            payload = {
                "job_category_id_list": [],
                "recruitment_id_list": [],
                "subject_id_list": [],
                "location_code_list": [],
                "tag_id_list": [],
                "keyword": "",
                "limit": page_size,
                "offset": page * page_size,
            }
            response = requests.post(
                BYTEDANCE_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            if body.get("code") not in (None, 0):
                raise ValueError(body.get("message") or "ByteDance API error")
            data = body.get("data", {})
            jobs = data.get("job_post_list", [])
            for posting in jobs:
                raw_id = posting.get("id")
                normalized.append(
                    _job(
                        "bytedance",
                        company,
                        raw_id,
                        posting.get("title"),
                        f"https://jobs.bytedance.com/en/position/{raw_id}/detail",
                        _location(
                            posting.get("city_info") or posting.get("location")
                        ),
                    )
                )
            total = data.get("count")
            if len(jobs) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (
        requests.RequestException,
        ValueError,
        AttributeError,
        TypeError,
    ) as error:
        return _failed("bytedance", company, error)
    return normalized


def _tesla_location(lookup: dict, value) -> str:
    if value in (None, ""):
        return "Unknown"
    if isinstance(value, (dict, list)):
        return _location(value)
    for collection in lookup.values():
        if isinstance(collection, dict):
            item = collection.get(str(value)) or collection.get(value)
            if item:
                return _location(item)
        elif isinstance(collection, list):
            for item in collection:
                if isinstance(item, dict) and str(item.get("id")) == str(value):
                    return _location(item)
    return str(value)


def fetch_tesla_jobs(options: dict) -> list[dict]:
    company = options.get("company", "Tesla")
    try:
        response = requests.get(
            TESLA_URL, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("response", body.get("data", body))
        listings = data.get("listings", data.get("jobs", []))
        lookup = data.get("lookup", {})
        normalized = []
        for posting in listings:
            raw_id = posting.get("id") or posting.get("jobId")
            # Tesla's board response normally uses compact keys (`t` title,
            # `l` location), while some regional versions return long names.
            title = (
                posting.get("title")
                or posting.get("jobTitle")
                or posting.get("t", "")
            )
            location_value = (
                posting.get("locations")
                or posting.get("location")
                or posting.get("locationId")
                or posting.get("jobLocation")
                or posting.get("l")
            )
            posting_url = (
                posting.get("jobUrl")
                or posting.get("url")
                or f"https://www.tesla.com/careers/search/job/{raw_id}"
            )
            normalized.append(
                _job(
                    "tesla",
                    company,
                    raw_id,
                    title,
                    urljoin("https://www.tesla.com", posting_url),
                    _tesla_location(lookup, location_value),
                )
            )
        return normalized
    except (requests.RequestException, ValueError, AttributeError) as error:
        # Tesla sometimes blocks cloud IPs. Do not stop every other company.
        return _failed("tesla", company, error)


def fetch_mcloud_jobs(options: dict) -> list[dict]:
    company = options["company"]
    page_size = 100
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 5))):
            response = requests.get(
                MCLOUD_URL,
                params={
                    "pageSize": page_size,
                    "offset": page * page_size,
                    "companyName": options["company_name"],
                    "customAttributeFilter": options["filter"],
                },
                headers=BROWSER_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            results = body.get("searchResults", [])
            for result in results:
                posting = result.get("job", result)
                place = ", ".join(
                    str(posting[key]).strip()
                    for key in (
                        "primary_city",
                        "primary_state",
                        "primary_country",
                    )
                    if posting.get(key)
                )
                normalized.append(
                    _job(
                        "mcloud",
                        company,
                        posting.get("id") or posting.get("requisition_id"),
                        posting.get("title"),
                        posting.get("url") or posting.get("seo_url"),
                        place,
                    )
                )
            total = body.get("totalHits")
            if len(results) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (
        requests.RequestException,
        ValueError,
        AttributeError,
        KeyError,
    ) as error:
        return _failed("mcloud", company, error)
    return normalized


def fetch_ashby_jobs(options: dict) -> list[dict]:
    company = options["company"]
    try:
        response = requests.get(
            ASHBY_URL.format(token=options["token"]),
            headers=BROWSER_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return [
            _job(
                "ashby",
                company,
                posting.get("id"),
                posting.get("title"),
                posting.get("jobUrl"),
                _location(posting.get("location")),
            )
            for posting in response.json().get("jobs", [])
            if posting.get("isListed", True)
        ]
    except (
        requests.RequestException,
        ValueError,
        AttributeError,
        KeyError,
    ) as error:
        return _failed("ashby", company, error)


def fetch_workday_jobs(options: dict) -> list[dict]:
    company = options["company"]
    host = options["host"].rstrip("/")
    tenant = options["tenant"]
    site = options["site"]
    page_size = 20
    normalized = []
    try:
        for page in range(int(options.get("max_pages", 10))):
            response = requests.post(
                WORKDAY_URL.format(
                    host=host,
                    tenant=tenant,
                    site=site,
                ),
                json={
                    "appliedFacets": {},
                    "limit": page_size,
                    "offset": page * page_size,
                    "searchText": "",
                },
                headers={**BROWSER_HEADERS, "Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            jobs = body.get("jobPostings", [])
            for posting in jobs:
                external_path = posting.get("externalPath", "")
                bullet_fields = posting.get("bulletFields") or []
                raw_id = (
                    bullet_fields[0]
                    if bullet_fields
                    else external_path.rstrip("/").split("/")[-1]
                )
                normalized.append(
                    _job(
                        "workday",
                        company,
                        raw_id,
                        posting.get("title"),
                        urljoin(
                            f"{host}/{site}/",
                            external_path.lstrip("/"),
                        ),
                        _location(
                            posting.get("locationsText")
                            or posting.get("location")
                        ),
                    )
                )
            total = body.get("total")
            if len(jobs) < page_size or (
                total is not None and len(normalized) >= int(total)
            ):
                break
    except (
        requests.RequestException,
        ValueError,
        AttributeError,
        KeyError,
    ) as error:
        return _failed("workday", company, error)
    return normalized


def fetch_seismic_jobs(options: dict) -> list[dict]:
    """Highspot careers now redirects to the consolidated Seismic board."""
    company = options.get("company", "Highspot / Seismic")
    board_url = options.get(
        "url", "https://www.seismic.com/careers/job-listings/"
    )
    try:
        response = requests.get(
            board_url, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        normalized = []
        seen_ids = set()
        for link in soup.select('a[href*="/careers/job-detail/?jid="]'):
            title = link.select_one("div.text-h6")
            if not title:
                continue
            posting_url = urljoin(board_url, link.get("href", ""))
            raw_id = (
                parse_qs(urlparse(posting_url).query).get("jid") or [None]
            )[0]
            if not raw_id or raw_id in seen_ids:
                continue
            seen_ids.add(raw_id)
            place = link.select_one("div.text-body2")
            normalized.append(
                _job(
                    "seismic",
                    company,
                    raw_id,
                    title.get_text(" ", strip=True),
                    posting_url,
                    place.get_text(" ", strip=True) if place else "Unknown",
                )
            )
        return normalized
    except (requests.RequestException, ValueError, AttributeError) as error:
        return _failed("seismic", company, error)


CONFIGURED_FETCHERS = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
    "amazon": fetch_amazon_jobs,
    "eightfold": fetch_eightfold_jobs,
    "google_careers": fetch_google_jobs,
    "ibm": fetch_ibm_jobs,
    "smartrecruiters": fetch_smartrecruiters_jobs,
    "oracle_recruiting": fetch_oracle_recruiting_jobs,
    "apple": fetch_apple_jobs,
    "bytedance": fetch_bytedance_jobs,
    "tesla": fetch_tesla_jobs,
    "mcloud": fetch_mcloud_jobs,
    "ashby": fetch_ashby_jobs,
    "workday": fetch_workday_jobs,
    "seismic": fetch_seismic_jobs,
}


def fetch_all_jobs(companies_config: dict) -> list[dict]:
    """Fetch all configured boards concurrently and isolate source failures."""
    tasks = []
    for config_key, fetcher in CONFIGURED_FETCHERS.items():
        tasks.extend(
            (fetcher, argument)
            for argument in companies_config.get(config_key, [])
        )

    if not tasks:
        return []

    all_jobs = []
    with ThreadPoolExecutor(max_workers=min(10, len(tasks))) as executor:
        futures = [
            executor.submit(fetcher, argument)
            for fetcher, argument in tasks
        ]
        for future in futures:
            try:
                all_jobs.extend(future.result())
            except Exception as error:
                print(f"[fetch_all_jobs] source failed: {error}")

    return list({posting["id"]: posting for posting in all_jobs}.values())
