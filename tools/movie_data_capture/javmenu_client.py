import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .storage import ActressWork


@dataclass(frozen=True)
class JavMenuSearchCard:
    video_code: str
    release_date: Optional[str]
    title: Optional[str]
    link: Optional[str]


class JavMenuClient:
    def __init__(self, base_url: str = "https://javmenu.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": f"{self.base_url}/",
            }
        )

    def _get(self, url: str, timeout: int = 15) -> requests.Response:
        return self.session.get(url, timeout=timeout)

    def _looks_like_homepage(self, url: str, response: requests.Response) -> bool:
        if response.url.rstrip("/") == f"{self.base_url}/en":
            return True
        if response.url.rstrip("/") == self.base_url:
            return True
        if response.history and response.url.rstrip("/") in (self.base_url, f"{self.base_url}/en"):
            return True
        return False

    def _video_page_url(self, video_code: str) -> str:
        code = video_code.strip().upper()
        return f"{self.base_url}/en/{code}"

    def _search_url(self, keyword: str, page: Optional[int] = None) -> str:
        kw = str(keyword).strip()
        url = f"{self.base_url}/en/search/{kw}"
        if page is not None:
            url = f"{url}?page={page}"
        return url

    def find_video_page_url(self, video_code: str) -> Optional[str]:
        code = video_code.strip().upper()

        direct_url = self._video_page_url(code)
        resp = self._get(direct_url)
        if resp.status_code == 200 and not self._looks_like_homepage(direct_url, resp):
            if code in resp.text:
                return resp.url

        search_url = self._search_url(code)
        resp = self._get(search_url)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            if f"/{code}" not in href:
                continue
            if "/search/" in href:
                continue
            if href.startswith(f"{self.base_url}/en/") or href.startswith("/en/"):
                return href if href.startswith("http") else f"{self.base_url}{href}"
        return None

    def get_video_info(self, video_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full video info including actress names, title, release date.
        """
        code = video_code.strip().upper()
        video_url = self.find_video_page_url(code)
        if not video_url:
            return None

        resp = self._get(video_url)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Parse Title (usually in h1 or h2 or .card-title)
        title = ""
        # Try finding title in .card-title which is common in javmenu for details
        # Or check h2
        title_tag = soup.find("h2")
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Parse Release Date
        # Usually in .row .col-md-X text-muted or strong tags. 
        # Structure varies, let's look for text pattern YYYY-MM-DD
        release_date = None
        date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
        # Search in the whole text or specific containers
        # Common container for info
        info_div = soup.select_one(".card-body") or soup
        date_match = date_pattern.search(info_div.get_text())
        if date_match:
            release_date = date_match.group(0)

        # Parse Actresses
        actress_links = soup.select("a.actress")
        names: List[str] = []
        if actress_links:
            female_links = [a for a in actress_links if "text-primary" not in (a.get("class") or [])]
            target = female_links if female_links else actress_links

            for link in target:
                actor_url = link.get("href")
                if not actor_url:
                    continue
                full = actor_url if actor_url.startswith("http") else f"{self.base_url}{actor_url}"
                try:
                    actor_resp = self._get(full, timeout=10)
                except Exception:
                    continue
                if actor_resp.status_code != 200:
                    continue
                actor_soup = BeautifulSoup(actor_resp.text, "html.parser")

                name = ""
                h2 = actor_soup.find("h2")
                if h2:
                    name = h2.get_text(strip=True)
                if not name and actor_soup.title and actor_soup.title.string:
                    name = actor_soup.title.string.strip()

                clean = name
                # Remove "Latest" prefix and "Videos" suffix if present, handling optional spaces
                clean = re.sub(r"^Latest\s*", "", clean, flags=re.IGNORECASE)
                clean = re.sub(r"\s*Videos$", "", clean, flags=re.IGNORECASE)
                clean = clean.strip()
                if clean:
                    names.append(clean)

        seen = set()
        deduped: List[str] = []
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            deduped.append(n)
            
        return {
            "video_code": code,
            "title": title,
            "release_date": release_date,
            "actresses": deduped,
            "link": video_url
        }

    def get_actress_names_by_video_code(self, video_code: str) -> List[str]:
        info = self.get_video_info(video_code)
        return info.get("actresses", []) if info else []

    def search_actress_works(
        self,
        actress_name: str,
        max_pages: Optional[int] = None,
        stop_if_exists_func: Optional[Callable[[str], bool]] = None,
    ) -> List[ActressWork]:
        name = actress_name.strip()
        if not name:
            return []

        first_url = self._search_url(name, page=1)
        resp = self._get(first_url)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")

        total_pages = 1
        jump_input = soup.select_one("#jump-to-page")
        if jump_input and jump_input.get("max"):
            try:
                total_pages = int(jump_input.get("max"))
            except Exception:
                total_pages = 1

        if max_pages is not None:
            total_pages = max(1, min(total_pages, int(max_pages)))

        works: List[ActressWork] = []
        for page in range(1, total_pages + 1):
            if page > 1:
                # Add delay to avoid crawler detection
                time.sleep(1)

            url = self._search_url(name, page=page)
            resp = self._get(url)
            if resp.status_code != 200:
                continue
            page_soup = BeautifulSoup(resp.text, "html.parser")
            cards = page_soup.select(".video-list-item .card")
            
            should_stop = False
            for card in cards:
                title_elem = card.select_one(".card-title")
                code = title_elem.get_text(strip=True) if title_elem else ""
                if not code or not re.search(r"\d", code):
                    continue
                
                # Check if we should stop
                normalized_code = code.strip().upper()
                if stop_if_exists_func and stop_if_exists_func(normalized_code):
                    should_stop = True
                    break

                date_elem = card.select_one(".text-muted")
                release_date = date_elem.get_text(strip=True) if date_elem else None
                desc_elem = card.select_one(".card-text")
                title = desc_elem.get_text(strip=True) if desc_elem else None
                link_elem = card.select_one("a[href]")
                link = None
                if link_elem:
                    href = link_elem.get("href")
                    link = urljoin(self.base_url, href) if href else None

                works.append(
                    ActressWork(
                        video_code=normalized_code,
                        release_date=release_date,
                        title=title,
                        link=link,
                    )
                )
            
            if should_stop:
                break

        uniq = {}
        for w in works:
            uniq[w.video_code] = w
        return list(uniq.values())
