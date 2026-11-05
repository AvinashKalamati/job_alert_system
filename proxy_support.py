"""Optional, single-proxy support for outbound job-board requests.

Credentials are supplied only through JOB_ALERT_PROXY_URL or a protected JSON
file named by JOB_ALERT_PROXY_FILE. Proxy pools and response-triggered proxy
rotation are deliberately not supported.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests


DEFAULT_PROXY_TEST_URL = "https://api.ipify.org?format=json"


def get_proxy_url() -> str | None:
    """Return the optional configured proxy URL without logging its value."""
    proxy_url = os.environ.get("JOB_ALERT_PROXY_URL", "").strip()
    if proxy_url:
        return _validate_proxy_url(proxy_url)

    config_path = os.environ.get("JOB_ALERT_PROXY_FILE", "").strip()
    if not config_path:
        return None

    path = Path(config_path)
    if path.stat().st_mode & 0o077:
        raise ValueError("proxy configuration file must not be group/world accessible")
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict) or not isinstance(config.get("proxy_url"), str):
        raise ValueError("proxy configuration must contain a string proxy_url")
    return _validate_proxy_url(config["proxy_url"].strip())


def get_proxy_mapping() -> dict[str, str] | None:
    """Return requests-compatible proxy settings, or None when disabled."""
    proxy_url = get_proxy_url()
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def configure_session(session) -> None:
    """Apply optional proxy settings to a requests.Session."""
    proxies = get_proxy_mapping()
    if proxies:
        session.proxies.update(proxies)


def proxy_connectivity_test(
    test_url: str | None = None, timeout: int = 15
) -> dict:
    """Call a public IP-echo endpoint through the configured proxy."""
    proxies = get_proxy_mapping()
    if not proxies:
        raise RuntimeError("no proxy configured")
    response = requests.get(
        test_url or os.environ.get("JOB_ALERT_PROXY_TEST_URL", DEFAULT_PROXY_TEST_URL),
        proxies=proxies,
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("proxy test returned an unexpected response")
    return body


def get_configured_positive_int(name: str, default: int) -> int:
    """Read a positive integer setting, falling back to its safe default."""
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _validate_proxy_url(proxy_url: str) -> str:
    parsed = urlparse(proxy_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("proxy URL must use http:// or https:// and include a host")
    return proxy_url
