
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class ActressWork:
    video_code: str
    release_date: Optional[str]
    title: Optional[str]
    link: Optional[str]

class MovieInfoProvider(ABC):
    @abstractmethod
    def get_video_info(self, video_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full details for a single video code.
        Returns dict with keys: video_code, title, release_date, actresses, link
        """
        pass

    @abstractmethod
    def get_actress_rank_list(self, page: int = 1) -> List[Dict[str, str]]:
        """
        Fetch list of actresses from ranking page.
        Returns list of dicts: {"name": str, "url": str}
        """
        pass

    @abstractmethod
    def get_videos_from_profile(self, profile_url: str, check_cancellation=None) -> List[ActressWork]:
        """
        Fetch all works from an actress's profile page (iterating all pages).
        Should return a list of ActressWork objects.
        """
        pass
