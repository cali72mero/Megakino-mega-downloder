from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio
from megakino.core.models import SearchResult, Episode, MediaDetails
from megakino.api.client import APIClient

async def search_for_movie(query: str, client: APIClient) -> List[SearchResult]:
    url = f"{client.base_url}/index.php?do=search&subaction=search&search_start=0&full_search=0&result_from=1&story={query}"
    response = await client.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    results = []
    for link in soup.find_all('a', class_='poster'):
        title_element = link.find('h3', class_='poster__title')
        if title_element:
            title = title_element.text.strip()
            href = link.get('href', '')
            if href.startswith('/'):
                href = client.base_url + href
            elif not href.startswith('http'):
                href = f"{client.base_url}/{href}"
            results.append(SearchResult(title=title, url=href))
    return results

async def get_media_details(url: str, client: APIClient) -> MediaDetails:
    try:
        response = await client.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        return MediaDetails(title="Error fetching details", episodes=[])
    
    og_title_meta = soup.find('meta', property='og:title')
    og_title = og_title_meta['content'] if og_title_meta and 'content' in og_title_meta.attrs else "Unknown Title"
    
    episodes = []
    
    # Try series select options
    try:
        series_select = soup.select('.pmovie__series-select select')
        if series_select:
            episode_options = series_select[0].find_all('option')
            for option in episode_options:
                ep_id = option.get('value')
                if not ep_id: continue
                
                ep_name = f"{og_title} - {option.text.strip()}"
                link_select = soup.find('select', {'id': ep_id})
                if link_select:
                    link_option = link_select.find('option')
                    if link_option and link_option.get('value'):
                        episodes.append(Episode(title=ep_name, url=link_option['value']))
    except Exception:
        pass
        
    # Search for all available mirrors in iframes (important for different providers)
    for iframe in soup.find_all('iframe'):
        data_src = iframe.get('data-src') or iframe.get('src')
        if data_src:
            provider_name = "Unbekannt"
            src_lower = data_src.lower()
            if "voe" in src_lower: provider_name = "VOE"
            elif "megakino" in src_lower: provider_name = "Megakino"
            elif "gxplayer" in src_lower: provider_name = "GXPlayer"
            elif "vidoza" in src_lower: provider_name = "Vidoza"
            elif "streamtape" in src_lower: provider_name = "Streamtape"
            elif "dood" in src_lower: provider_name = "DoodStream"
            elif "waaw" in src_lower: provider_name = "WAAW"
            
            if provider_name != "Unbekannt":
                # Only add if not already in the list to avoid duplicates
                mirror_url = data_src
                if mirror_url.startswith('//'):
                    mirror_url = f"https:{mirror_url}"
                    
                is_duplicate = any(mirror_url == e.url for e in episodes)
                if not is_duplicate:
                    episodes.append(Episode(title=f"{og_title} ({provider_name} Mirror)", url=mirror_url))

    return MediaDetails(title=og_title, episodes=episodes)

def get_megakino_iframes(html_content: bytes) -> List[str]:
    soup = BeautifulSoup(html_content, 'html.parser')
    iframe_tag = soup.find('iframe', src=True)
    if iframe_tag:
        return [iframe_tag['src']]
    return []
