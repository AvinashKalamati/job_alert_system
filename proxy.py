import requests
from pathlib import Path

proxy_file = Path("secrets/proxies.txt")

for line in proxy_file.read_text().splitlines():
    if not line.strip():
        continue

    ip, port, username, password = line.strip().split(":", 3)

    proxy_url = f"http://{username}:{password}@{ip}:{port}"

    try:
        response = requests.get(
            "https://httpbin.org/ip",
            proxies={
                "http": proxy_url,
                "https": proxy_url,
            },
            timeout=15,
        )
        response.raise_for_status()

        print(f"Proxy {ip}:{port} -> {response.json()}")

    except requests.RequestException as error:
        print(f"Proxy {ip}:{port} failed: {type(error).__name__}")