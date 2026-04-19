import asyncio
from typing import Optional

import httpx
from cachetools import TTLCache
from fake_useragent import UserAgent

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DOMAIN_SOURCE_URL = (
    "https://raw.githubusercontent.com/Yezun-hikari/new-domain-check/refs/heads/main/"
    "monitors/megakino/domain.txt"
)

# Cache for 1 hour (3600 seconds)
domain_cache = TTLCache(maxsize=1, ttl=3600)


async def get_latest_domain() -> str:
    if "base_url" in domain_cache:
        return domain_cache["base_url"]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(DOMAIN_SOURCE_URL)
        response.raise_for_status()
        domain = response.text.strip()
        for prefix in ("https://", "http://"):
            if domain.startswith(prefix):
                domain = domain[len(prefix) :]
        if not domain or "/" in domain:
            raise ValueError("Domain source returned an invalid host name.")
        base_url = f"https://{domain}"
        domain_cache["base_url"] = base_url
        return base_url


class APIClient:
    def __init__(self):
        self.ua = self._make_user_agent()
        self.limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.ua},
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            limits=self.limits,
            verify=True,
        )
        self.base_url = None

    @staticmethod
    def _make_user_agent() -> str:
        try:
            return UserAgent().random
        except Exception:
            return DEFAULT_USER_AGENT

    async def get_latest_pypi_version(self) -> Optional[str]:
        try:
            response = await self.client.get(
                "https://pypi.org/pypi/megakino-mega-downloader/json",
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("info", {}).get("version")
        except Exception:
            pass
        return None

    async def initialize(self):
        try:
            self.base_url = await get_latest_domain()
            for _ in range(3):
                try:
                    response = await self.client.get(f"{self.base_url}/index.php?yg=token")
                    response.raise_for_status()
                    break
                except httpx.RequestError:
                    await asyncio.sleep(1)
        except Exception as e:
            raise RuntimeError(f"Initialization failed: {e}") from e

    async def get(self, url: str) -> httpx.Response:
        response = await self.client.get(url)
        response.raise_for_status()
        return response

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
