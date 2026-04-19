from typing import Awaitable, Callable, Dict, Iterable, Optional, Tuple, Union

from megakino.api.client import APIClient
from megakino.api.extractors.megakino import megakino_get_direct_link
from megakino.api.extractors.voe import voe_get_direct_link
from megakino.core.models import Episode, FailedEpisode, ResolvedEpisode, StreamResolution

Extractor = Callable[[str, APIClient], Awaitable[Optional[str]]]

EXTRACTORS: Dict[str, Extractor] = {
    "Megakino": megakino_get_direct_link,
    "VOE": voe_get_direct_link,
}


def normalize_episode(episode: Union[Episode, dict]) -> Episode:
    if isinstance(episode, Episode):
        return episode
    return Episode(**episode)


def provider_order(preferred_provider: str) -> Tuple[str, str]:
    primary = preferred_provider if preferred_provider in EXTRACTORS else "Megakino"
    fallback = "VOE" if primary == "Megakino" else "Megakino"
    return primary, fallback


async def resolve_episode_stream(
    episode: Union[Episode, dict],
    client: APIClient,
    preferred_provider: str,
) -> Union[ResolvedEpisode, FailedEpisode]:
    normalized_episode = normalize_episode(episode)
    primary, fallback = provider_order(preferred_provider)

    for provider in (primary, fallback):
        direct_link = await EXTRACTORS[provider](normalized_episode.url, client)
        if direct_link:
            return ResolvedEpisode(
                episode=normalized_episode,
                direct_link=direct_link,
                provider=provider,
            )

    return FailedEpisode(
        episode=normalized_episode,
        primary_provider=primary,
        fallback_provider=fallback,
    )


async def resolve_episode_streams(
    episodes: Iterable[Union[Episode, dict]],
    client: APIClient,
    preferred_provider: str,
) -> StreamResolution:
    resolution = StreamResolution()

    for episode in episodes:
        result = await resolve_episode_stream(episode, client, preferred_provider)
        if isinstance(result, ResolvedEpisode):
            resolution.resolved.append(result)
        else:
            resolution.failed.append(result)

    return resolution
