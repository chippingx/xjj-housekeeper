from typing import List, Optional, Set

from .javmenu_client import JavMenuClient
from .storage import ActressWork, MovieDataStorage, MovieInfoRow, get_default_database_path


class MovieDataCaptureService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_default_database_path()
        self.storage = MovieDataStorage(self.db_path)
        self.client = JavMenuClient()

    def close(self) -> None:
        self.storage.close()

    def get_actress_names_by_video_code(self, video_code: str, force_refresh: bool = False) -> List[str]:
        code = (video_code or "").strip().upper()
        if not code:
            return []
        if not force_refresh:
            cached = self.storage.get_actresses_by_video_code(code)
            if cached:
                return cached

        # Logic changed: now we try to get full info (title, date, actresses) from the video page
        # to avoid inserting partial records.
        info = self.client.get_video_info(code)
        if not info:
             return []
        
        # info is expected to be a dict or object with keys: actresses, title, release_date, link, video_code
        names = info.get("actresses", [])
        if names:
            for name in names:
                self.storage.add_video_actress_relationship(
                    video_code=info["video_code"],
                    actress_name=name,
                    source="javmenu",
                    title=info.get("title"),
                    release_date=info.get("release_date"),
                    link=info.get("link")
                )
        return names

    def get_works_by_actress_name(
        self, actress_name: str, force_refresh: bool = False
    ) -> List[ActressWork]:
        name = (actress_name or "").strip()
        if not name:
            return []
        
        # 1. Get existing works from DB
        cached_works = self.storage.get_works_by_actress_name(name) or []
        existing_codes = {w.video_code for w in cached_works}
        
        if not force_refresh and cached_works:
             # Logic: if we have cached works, we only want to fetch *new* ones.
             # We assume the website lists newest first.
             # We pass a callback to stop fetching when we hit a known code.
             
             def stop_check(code: str) -> bool:
                 return code in existing_codes
             
             new_works = self.client.search_actress_works(name, stop_if_exists_func=stop_check)
             
             if new_works:
                 self.storage.replace_works_for_actress_name(name, new_works + cached_works, source="javmenu")
                 # Re-read to get sorted/deduplicated list or just merge in memory
                 # Ideally replace_works_for_actress_name handles the merge or we just insert new ones.
                 # The current implementation of replace_works_for_actress_name DELETES all and re-inserts.
                 # So we need to pass the FULL list.
                 return new_works + cached_works
             else:
                 return cached_works
        
        # If no cache or force refresh, fetch all
        works = self.client.search_actress_works(name)
        if works:
            self.storage.replace_works_for_actress_name(name, works, source="javmenu")
        return works

    def search_movie_info(self, keyword: str, search_type: str) -> List[MovieInfoRow]:
        """
        Search movie info by actress or video code.
        Ensures data is fetched from web if not present (or updated).
        """
        kw = (keyword or "").strip()
        if not kw:
            return []
            
        if search_type == "actress":
            self.get_works_by_actress_name(kw)
            return self.storage.query_movie_info(kw, "actress")
        elif search_type == "video":
            self.get_actress_names_by_video_code(kw)
            return self.storage.query_movie_info(kw, "video")
        else:
            return []
