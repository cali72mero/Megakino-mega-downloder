from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from megakino.api.client import APIClient
from megakino.core.models import Episode, MediaDetails, SearchResult


def parse_search_results(html_content: bytes, base_url: str) -> List[SearchResult]:
    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    seen_urls = set()

    for link in soup.find_all("a", class_="poster"):
        title_element = link.find("h3", class_="poster__title")
        href = link.get("href", "")
        if not title_element or not href:
            continue

        url = urljoin(f"{base_url.rstrip('/')}/", href)
        if url in seen_urls:
            continue

        seen_urls.add(url)
        results.append(SearchResult(title=title_element.text.strip(), url=url))

    return results


async def search_for_movie(query: str, client: APIClient) -> List[SearchResult]:
    response = await client.client.get(
        f"{client.base_url}/index.php",
        params={
            "do": "search",
            "subaction": "search",
            "search_start": 0,
            "full_search": 0,
            "result_from": 1,
            "story": query,
        },
    )
    response.raise_for_status()
    return parse_search_results(response.content, client.base_url)


def parse_media_details(html_content: bytes) -> MediaDetails:
    soup = BeautifulSoup(html_content, "html.parser")

    og_title_meta = soup.find("meta", property="og:title")
    og_title = (
        og_title_meta["content"].strip()
        if og_title_meta and "content" in og_title_meta.attrs
        else "Unknown Title"
    )

    episodes = []
    seen_urls = set()

    series_select = soup.select(".pmovie__series-select select")
    if series_select:
        for option in series_select[0].find_all("option"):
            ep_id = option.get("value")
            if not ep_id:
                continue

            link_select = soup.find("select", {"id": ep_id})
            link_option = link_select.find("option") if link_select else None
            episode_url = link_option.get("value") if link_option else None
            if not episode_url or episode_url in seen_urls:
                continue

            seen_urls.add(episode_url)
            ep_name = f"{og_title} - {option.text.strip()}"
            episodes.append(Episode(title=ep_name, url=episode_url))

    provider_markers = {
        "voe": "VOE",
        "megakino": "Megakino",
        "gxplayer": "GXPlayer",
        "vidoza": "Vidoza",
        "streamtape": "Streamtape",
        "dood": "DoodStream",
        "waaw": "WAAW",
    }

    for iframe in soup.find_all("iframe"):
        data_src = iframe.get("data-src") or iframe.get("src")
        if not data_src:
            continue

        src_lower = data_src.lower()
        provider_name = next(
            (name for marker, name in provider_markers.items() if marker in src_lower),
            None,
        )
        if not provider_name:
            continue

        mirror_url = f"https:{data_src}" if data_src.startswith("//") else data_src
        if mirror_url in seen_urls:
            continue

        seen_urls.add(mirror_url)
        episodes.append(Episode(title=f"{og_title} ({provider_name} Mirror)", url=mirror_url))

    return MediaDetails(title=og_title, episodes=episodes)


async def get_media_details(url: str, client: APIClient) -> MediaDetails:
    response = await client.get(url)
    return parse_media_details(response.content)


def get_megakino_iframes(html_content: bytes) -> List[str]:
    soup = BeautifulSoup(html_content, "html.parser")
    iframe_tag = soup.find("iframe", src=True)
    if iframe_tag:
        return [iframe_tag["src"]]
    return []
