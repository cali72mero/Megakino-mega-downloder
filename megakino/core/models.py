from dataclasses import dataclass, field
from typing import Dict, Optional, List

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
