import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ActressWork:
    video_code: str
    release_date: Optional[str]
    title: Optional[str]
    link: Optional[str]


@dataclass(frozen=True)
class MovieInfoRow:
    actress_name: str
    video_code: str
    release_date: Optional[str]
    updated_at: str
    title: Optional[str] = None


class MovieDataStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_parent_dir()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()
        self._create_indexes()

    def close(self) -> None:
        try:
            self.connection.close()
        except Exception:
            pass

    def _ensure_parent_dir(self) -> None:
        if self.db_path in (":memory:", ""):
            return
        parent = Path(self.db_path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)

    def _create_tables(self) -> None:
        cur = self.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS movie_actress_works (
                actress_name TEXT NOT NULL,
                video_code TEXT NOT NULL,
                release_date TEXT,
                title TEXT,
                link TEXT,
                source TEXT,
                fetched_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                other_name1 TEXT,
                other_name2 TEXT,
                other_name3 TEXT,
                PRIMARY KEY (actress_name, video_code)
            )
            """
        )
        # Check and add new columns if missing (for existing DB)
        cur.execute("PRAGMA table_info(movie_actress_works)")
        columns = [row[1] for row in cur.fetchall()]
        if "other_name1" not in columns:
            cur.execute("ALTER TABLE movie_actress_works ADD COLUMN other_name1 TEXT")
        if "other_name2" not in columns:
            cur.execute("ALTER TABLE movie_actress_works ADD COLUMN other_name2 TEXT")
        if "other_name3" not in columns:
            cur.execute("ALTER TABLE movie_actress_works ADD COLUMN other_name3 TEXT")

        self.connection.commit()

    def _create_indexes(self) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_movie_actress_works_actress_name ON movie_actress_works(actress_name)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_movie_actress_works_video_code ON movie_actress_works(video_code)"
        )
        self.connection.commit()

    def query_movie_info(self, keyword: str, by: str) -> List[MovieInfoRow]:
        if not keyword:
            return []
        kw = keyword.strip()
        cur = self.connection.cursor()
        
        if by == "actress":
            cur.execute(
                """
                SELECT actress_name, video_code, release_date, updated_at, title
                FROM movie_actress_works
                WHERE actress_name = ?
                ORDER BY release_date DESC, video_code DESC
                """,
                (kw,),
            )
        elif by == "video":
            code = kw.upper()
            cur.execute(
                """
                SELECT actress_name, video_code, release_date, updated_at, title
                FROM movie_actress_works
                WHERE video_code = ?
                ORDER BY actress_name ASC
                """,
                (code,),
            )
        elif by == "all":
            like_kw = f"%{kw}%"
            cur.execute(
                """
                SELECT actress_name, video_code, release_date, updated_at, title
                FROM movie_actress_works
                WHERE video_code LIKE ? OR actress_name LIKE ?
                ORDER BY release_date DESC
                """,
                (like_kw, like_kw),
            )
        else:
            return []

        rows = cur.fetchall()
        return [
            MovieInfoRow(
                actress_name=row["actress_name"],
                video_code=row["video_code"],
                release_date=row["release_date"],
                updated_at=row["updated_at"],
                title=row["title"],
            )
            for row in rows
        ]

    def check_existence(self, actress_name: str, video_code: str) -> bool:
        """Check if a specific actress-video relationship exists."""
        if not actress_name or not video_code:
            return False
        cur = self.connection.cursor()
        cur.execute(
            "SELECT 1 FROM movie_actress_works WHERE actress_name = ? AND video_code = ?",
            (actress_name.strip(), video_code.strip().upper()),
        )
        return cur.fetchone() is not None

    def get_actresses_by_video_code(self, video_code: str) -> Optional[List[str]]:
        if not video_code:
            return None
        code = video_code.strip().upper()
        cur = self.connection.cursor()
        cur.execute(
            "SELECT DISTINCT actress_name FROM movie_actress_works WHERE video_code = ?",
            (code,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        names = sorted(list(set(row["actress_name"] for row in rows if row["actress_name"])))
        return names if names else None

    def add_video_actress_relationship(
        self,
        video_code: str,
        actress_name: str,
        source: str,
        title: Optional[str] = None,
        release_date: Optional[str] = None,
        link: Optional[str] = None,
    ) -> None:
        code = video_code.strip().upper()
        name = actress_name.strip()
        if not code or not name:
            return
        # Use 'YYYY-MM-DD hh:mm:ss' format
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.connection.cursor()
        cur.execute(
            """
            INSERT INTO movie_actress_works (
                actress_name, video_code, source, fetched_at, updated_at, title, release_date, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(actress_name, video_code) DO UPDATE SET
                title = COALESCE(excluded.title, movie_actress_works.title),
                release_date = COALESCE(excluded.release_date, movie_actress_works.release_date),
                link = COALESCE(excluded.link, movie_actress_works.link),
                updated_at = excluded.updated_at
            """,
            (name, code, source, now, now, title, release_date, link),
        )
        self.connection.commit()

    def get_works_by_actress_name(self, actress_name: str) -> Optional[List[ActressWork]]:
        if not actress_name:
            return None
        name = actress_name.strip()
        cur = self.connection.cursor()
        cur.execute(
            """
            SELECT video_code, release_date, title, link
            FROM movie_actress_works
            WHERE actress_name = ?
            ORDER BY release_date DESC, video_code DESC
            """,
            (name,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        works = [
            ActressWork(
                video_code=row["video_code"],
                release_date=row["release_date"],
                title=row["title"],
                link=row["link"],
            )
            for row in rows
        ]
        return works

    def replace_works_for_actress_name(self, actress_name: str, works: List[ActressWork], source: str) -> None:
        name = actress_name.strip()
        # Use 'YYYY-MM-DD hh:mm:ss' format
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.connection.cursor()
        
        # We need to preserve existing aliases if we are replacing works?
        # But 'replace_works_for_actress_name' deletes ALL works for this actress.
        # This means we lose aliases if they are stored in this table (which they are, redundantly for each row).
        # Wait, if aliases are per-actress, storing them in (actress, video) PK table means they are duplicated.
        # And deleting works deletes aliases. This is bad design if we want to keep aliases.
        # However, following the current instruction, we just added columns.
        # To mitigate data loss, we should read existing aliases first (from any row), then re-insert them.
        
        cur.execute("SELECT other_name1, other_name2, other_name3 FROM movie_actress_works WHERE actress_name = ? LIMIT 1", (name,))
        row = cur.fetchone()
        aliases = (row["other_name1"], row["other_name2"], row["other_name3"]) if row else (None, None, None)
        
        cur.execute("DELETE FROM movie_actress_works WHERE actress_name = ?", (name,))
        cur.executemany(
            """
            INSERT INTO movie_actress_works (
                actress_name, video_code, release_date, title, link, source, fetched_at, updated_at,
                other_name1, other_name2, other_name3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    name,
                    w.video_code.strip().upper(),
                    w.release_date,
                    w.title,
                    w.link,
                    source,
                    now,
                    now,
                    aliases[0], aliases[1], aliases[2]
                )
                for w in works
                if w.video_code and w.video_code.strip()
            ],
        )
        self.connection.commit()


def get_default_database_path() -> str:
    env_db = os.getenv("MOVIE_DATA_CAPTURE_DB_PATH")
    if env_db:
        return env_db
    try:
        from tools.video_info_collector.cli import get_default_paths

        return get_default_paths()["default_database"]
    except Exception:
        return "output/video_info_collector/database/video_database.db"
