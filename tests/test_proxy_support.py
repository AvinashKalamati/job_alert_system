import os
import unittest
from unittest.mock import patch

import fetchers
import proxy_support


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class ProxySupportTests(unittest.TestCase):
    def test_no_proxy_configuration_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(proxy_support.get_proxy_mapping())

    def test_proxy_url_environment_variable_supports_credentials(self):
        with patch.dict(os.environ, {
            "JOB_ALERT_PROXY_URL": "http://user:password@proxy.internal:8080",
        }, clear=True):
            self.assertEqual(
                proxy_support.get_proxy_mapping(),
                {
                    "http": "http://user:password@proxy.internal:8080",
                    "https": "http://user:password@proxy.internal:8080",
                },
            )

    @patch("proxy_support.requests.get")
    def test_proxy_connectivity_test_uses_configured_proxy(self, get):
        get.return_value = FakeResponse({"ip": "203.0.113.10"})
        with patch.dict(os.environ, {
            "JOB_ALERT_PROXY_URL": "https://proxy.internal:8443",
        }, clear=True):
            self.assertEqual(
                proxy_support.proxy_connectivity_test("https://echo.example/ip"),
                {"ip": "203.0.113.10"},
            )
        self.assertEqual(
            get.call_args.kwargs["proxies"]["https"],
            "https://proxy.internal:8443",
        )

    def test_invalid_proxy_url_is_rejected(self):
        with patch.dict(os.environ, {
            "JOB_ALERT_PROXY_URL": "socks5://proxy.internal:1080",
        }, clear=True):
            with self.assertRaises(ValueError):
                proxy_support.get_proxy_mapping()

    @patch("fetchers.requests.get")
    def test_fetcher_uses_configured_proxy(self, get):
        get.return_value = FakeResponse({"jobs": []})
        with patch.dict(os.environ, {
            "JOB_ALERT_PROXY_URL": "http://proxy.internal:8080",
        }, clear=True):
            fetchers.fetch_greenhouse_jobs("example")
        self.assertEqual(
            get.call_args.kwargs["proxies"],
            {
                "http": "http://proxy.internal:8080",
                "https": "http://proxy.internal:8080",
            },
        )


if __name__ == "__main__":
    unittest.main()
