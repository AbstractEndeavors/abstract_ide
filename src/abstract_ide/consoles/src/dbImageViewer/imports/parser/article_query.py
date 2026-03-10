from dataclasses import dataclass
from typing import Optional, Sequence

@dataclass
class ArticleQuery:
    user: Optional[str] = None
    page: int = 1
    media_type: Optional[str] = None
    required_tags: Sequence[str] | None = None
    raw_url: Optional[str] = None
