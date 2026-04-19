from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    title: str
    url: str


@dataclass
class Episode:
    title: str
    url: str


@dataclass
class MediaDetails:
    title: str
    episodes: List[Episode] = field(default_factory=list)


@dataclass
class ResolvedEpisode:
    episode: Episode
    direct_link: str
    provider: str


@dataclass
class FailedEpisode:
    episode: Episode
    primary_provider: str
    fallback_provider: Optional[str] = None


@dataclass
class StreamResolution:
    resolved: List[ResolvedEpisode] = field(default_factory=list)
    failed: List[FailedEpisode] = field(default_factory=list)
