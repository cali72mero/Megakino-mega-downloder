import httpx
from fake_useragent import UserAgent
from typing import Optional
from cachetools import TTLCache
import asyncio

# Cache for 1 hour (3600 seconds)
domain_cache = TTLCache(maxsize=1, ttl=3600)

async def get_latest_domain() -> str:
    if "base_url" in domain_cache:
        return domain_cache["base_url"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://raw.githubusercontent.com/Yezun-hikari/new-domain-check/refs/heads/main/monitors/megakino/domain.txt",
            timeout=15.0
        )
        response.raise_for_status()
        base_url = f"https://{response.text.strip()}"
        domain_cache["base_url"] = base_url
        return base_url

class APIClient:
    def __init__(self):
        self.ua = UserAgent().random
        # Use a more robust SSL context and retries
        self.limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.ua},
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            limits=self.limits,
            verify=True # Ensure SSL verification is ON for security
        )
        self.base_url = None

    async def get_latest_pypi_version(self) -> Optional[str]:
        try:
            # Query PyPI JSON API for the package info
            response = await self.client.get("https://pypi.org/pypi/megakino-mega-downloader/json", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("info", {}).get("version")
        except Exception:
            pass # Fail silently if PyPI is unreachable
        return None

    async def initialize(self):
        try:
            self.base_url = await get_latest_domain()
            # Fetch token with retry logic
            for _ in range(3):
                try:
                    await self.client.get(f"{self.base_url}/index.php?yg=token")
                    break
                except httpx.RequestError:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Initialization Error: {e}")

    async def get(self, url: str) -> httpx.Response:
        return await self.client.get(url)

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
