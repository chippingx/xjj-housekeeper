from typing import List, Optional, Set
from .impl.javmenu_client import JavMenuClient
from .storage import ActressWork, MovieDataStorage, MovieInfoRow, get_default_database_path
# Import SQLiteStorage to access local video info
from tools.video_info_collector.sqlite_storage import SQLiteStorage

class MovieDataCaptureService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_default_database_path()
        self.storage = MovieDataStorage(self.db_path)
        # Assuming shared DB path for both tools as observed
        self.local_storage = SQLiteStorage(self.db_path)
        self.client = JavMenuClient()

    def close(self) -> None:
        self.storage.close()

    def search_movie_info(self, keyword: str, search_type: str = "all", check_cancellation=None) -> List[MovieInfoRow]:
        if check_cancellation:
            # If check_cancellation is provided, it implies a "Pull" operation (fetch from network)
            if search_type == "video":
                self.sync_by_video_code(keyword)
            elif search_type == "actress":
                self.sync_by_actress(keyword)
        
        return self.storage.query_movie_info(keyword, search_type)

    def get_actress_names_by_video_code(self, video_code: str, force_refresh: bool = False) -> List[str]:
        code = (video_code or "").strip().upper()
        if not code:
            return []
        
        # Check if we already have this video info in DB (and it has actress info)
        # However, storage.get_actresses_by_video_code returns None if not found, or list if found.
        # Even if list is empty (no actress found but record exists?), current storage doesn't differentiate well 
        # because it queries 'movie_actress_works'. If a video has NO actresses, it might not be in this table 
        # unless we store a dummy record? Currently we don't.
        # So "exists" implies we have found actresses for it.
        # If we want to skip "already processed but no actress found", we might need a separate table or flag.
        # For now, we assume if it's in DB, we skip.
        
        if not force_refresh:
            cached = self.storage.get_actresses_by_video_code(code)
            if cached:
                print(f"Skipping {code} (already in DB)")
                return cached

        print(f"Fetching details for {code}...")
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
        self, actress_name: str, force_refresh: bool = False, check_cancellation=None
    ) -> List[ActressWork]:
        name = (actress_name or "").strip()
        if not name:
            return []
        
        if check_cancellation and check_cancellation():
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
             
             new_works = self.client.search_actress_works(name, stop_if_exists_func=stop_check, check_cancellation=check_cancellation)
             
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
        works = self.client.search_actress_works(name, check_cancellation=check_cancellation)
        if works:
            self.storage.replace_works_for_actress_name(name, works, source="javmenu")
        return works

    def sync_by_video_code(self, video_code: str) -> bool:
        """
        Sync info for a single video code.
        """
        code = video_code.strip().upper()
        print(f"Syncing video: {code}...")
        
        # This calls get_video_info inside, which is what we want for detail mode
        actresses = self.get_actress_names_by_video_code(code, force_refresh=True)
        if actresses:
            print(f"  Found actresses: {actresses}")
            return True
        else:
            # Maybe it has no actresses but we still fetched title/date?
            # get_actress_names_by_video_code returns empty list if no actresses found, 
            # BUT it still calls add_video_actress_relationship if it found info?
            # Actually get_actress_names_by_video_code implementation:
            # calls client.get_video_info(code)
            # if info: iterates actresses and adds relationship.
            # If NO actresses, it does NOT add relationship for title/date currently?
            # Let's check get_actress_names_by_video_code implementation.
            # It only loops `if names:`.
            # We should probably fix that to save video info even if no actress found?
            # But the table is `movie_actress_works`, PK is (actress, video).
            # If no actress, we can't store it in THIS table.
            # So returning False is correct for this table design.
            print(f"  No actresses found for {code}.")
            return False

    def sync_local_videos(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        Sync info for all local videos found in video_master_list.
        Only fetches if not already present in movie_actress_works.
        
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        # Get all active video codes from master list
        master_list = self.local_storage.get_all_master_list()
        # Filter active only
        codes = [entry['video_code'] for entry in master_list if entry.get('status') == 'active']
        
        print(f"Found {len(codes)} active local videos. Starting sync...")
        count = 0
        for code in codes:
            # Note: For local videos, we can't filter by release date BEFORE fetching because we don't know it yet (unless it's in DB).
            # But get_actress_names_by_video_code returns cached data if available.
            # If we want to filter by date, we should probably fetch first, then check date?
            # User requirement: "For --local also hope can work with --between".
            # This implies if the fetched video's release date is NOT in range, we might not count it?
            # Or maybe the user means "Only fetch for videos that we THINK are in range"? But we don't know.
            # Let's assume we fetch, and if date is out of range, we print "Skipped due to date" and don't count it?
            # But the primary purpose is to POPULATE the DB. Not populating it because it's old seems counter-intuitive for "sync local".
            # However, if the user explicitly asks for it...
            
            # Let's just fetch it. The "skip" logic inside get_actress... handles DB existence.
            # If the user really wants to filter what is PROCESSED, we can check the result.
            
            actresses = self.get_actress_names_by_video_code(code)
            
            # Post-fetch filter (optional, just for reporting)
            if start_date or end_date:
                # We need to query the release date to check
                info = self.storage.query_movie_info(code, "video")
                if info:
                    rdate = info[0].release_date
                    if rdate:
                        if start_date and rdate < start_date:
                            continue
                        if end_date and rdate > end_date:
                            continue
            
            count += 1
            
        return count

    def sync_by_date_range(self, start_date: str, end_date: str, max_pages: int = 100) -> int:
        """
        Sync movies released within a specific date range.
        """
        print(f"Syncing movies between {start_date} and {end_date}...")
        # We use start_date as 'since_date' for the client to know when to stop (approximately)
        # But since client iterates pages (descending date), stopping at start_date is correct.
        # However, we also need to filter out videos NEWER than end_date.
        
        works = self.client.get_recent_movies(since_date=start_date, max_pages=max_pages)
        if not works:
            print("No recent movies found.")
            return 0
        
        # Filter by end_date and start_date strictly
        filtered_works = []
        for w in works:
            if not w.release_date:
                continue
            if w.release_date < start_date:
                continue
            if w.release_date > end_date:
                continue
            filtered_works.append(w)
            
        print(f"Found {len(filtered_works)} videos in range {start_date} - {end_date}. Processing...")
        count = 0
        for w in filtered_works:
            if not w.video_code:
                continue
            self.get_actress_names_by_video_code(w.video_code)
            count += 1
        return count

    def sync_by_profile_url(self, profile_url: str, actress_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        Sync movies from an actress profile page.
        """
        print(f"Fetching videos from profile: {profile_url} for {actress_name}")
        
        # Try to get the full name from the profile page to fix potential truncation
        real_name = self.client.get_actress_name_from_profile(profile_url)
        effective_name = real_name if real_name else actress_name
        if real_name and real_name != actress_name:
            print(f"  Corrected actress name: {actress_name} -> {effective_name}")

        works = self.client.get_videos_from_profile(profile_url)
        if not works:
            print(f"No works found in profile for {effective_name}")
            return 0
            
        count = 0
        for w in works:
            # Date filter
            if start_date or end_date:
                if not w.release_date:
                    continue
                if start_date and w.release_date < start_date:
                    continue
                if end_date and w.release_date > end_date:
                    continue
            
            # Idempotency check: if record exists, skip
            if self.storage.check_existence(effective_name, w.video_code):
                continue

            self.storage.add_video_actress_relationship(
                video_code=w.video_code,
                actress_name=effective_name,
                source="javmenu_profile",
                title=w.title,
                release_date=w.release_date,
                link=w.link
            )
            count += 1
            
        print(f"  Saved {count} videos for {effective_name}")
        return count

    def sync_full_actress_rank(self, max_rank_pages: int = 6, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        Sync all actresses from the rank list.
        """
        print(f"Syncing full actress rank (pages 1-{max_rank_pages})...")
        total_videos = 0
        
        for page in range(1, max_rank_pages + 1):
            print(f"Processing rank page {page}...")
            actresses = self.client.get_actress_rank_list(page)
            if not actresses:
                print(f"No actresses found on rank page {page}")
                break
                
            for item in actresses:
                name = item["name"]
                url = item["url"]
                
                count = self.sync_by_profile_url(url, name, start_date, end_date)
                total_videos += count
                
        return total_videos

    def sync_by_actress(self, actress_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        Sync all movies for a specific actress using efficient profile lookup.
        """
        print(f"Syncing movies for actress: {actress_name}...")
        
        # 1. Try to find profile URL first
        print(f"Searching for profile URL for {actress_name}...")
        profile_url = self.client.find_actress_profile_url(actress_name)
        
        if profile_url:
            print(f"Found profile URL: {profile_url}")
            return self.sync_by_profile_url(profile_url, actress_name, start_date, end_date)
        else:
            print(f"Could not find direct profile URL for {actress_name}. Falling back to search method (filtered)...")
            # Fallback to the search method (but stricter)
            # Copy of previous logic but maybe slightly optimized?
            # Actually, previous logic was: Search -> Get List -> Detail Check.
            # That logic is robust enough as a fallback.
            
            works = self.client.search_actress_works(actress_name)
            if not works:
                print(f"No works found for {actress_name} via search.")
                return 0
                
            filtered_works = []
            for w in works:
                if not w.video_code: continue
                if start_date or end_date:
                    if not w.release_date: continue
                    if start_date and w.release_date < start_date: continue
                    if end_date and w.release_date > end_date: continue
                filtered_works.append(w)

            print(f"Found {len(filtered_works)} works via search. Verifying...")
            
            count = 0
            target_normalized = actress_name.strip().replace(" ", "").lower()
            
            for w in filtered_works:
                actresses = self.get_actress_names_by_video_code(w.video_code)
                found = False
                for name in actresses:
                    norm = name.strip().replace(" ", "").lower()
                    if target_normalized in norm or norm in target_normalized:
                        found = True
                        break
                
                if found:
                    count += 1
                else:
                    # Title match fallback
                    match_title = False
                    if w.title:
                        norm_title = w.title.strip().replace(" ", "").lower()
                        if target_normalized in norm_title:
                            match_title = True
                    
                    if match_title:
                        print(f"  [Info] Match found in title for {w.video_code}: {w.title}. Adding relationship.")
                        self.storage.add_video_actress_relationship(
                            video_code=w.video_code,
                            actress_name=actress_name,
                            source="javmenu_title_match",
                            title=w.title,
                            release_date=w.release_date,
                            link=w.link
                        )
                        count += 1
                    else:
                         print(f"  [Info] Video {w.video_code} fetched but {actress_name} not found in actress list.")
                         
            return count
