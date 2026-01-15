from pathlib import Path

from tools.movie_data_capture.cache import ActressWork, MovieDataCache
from tools.movie_data_capture.service import MovieDataCaptureService


class _FakeClient:
    def __init__(self):
        self.actress_calls = 0
        self.works_calls = 0

    def get_actress_names_by_video_code(self, video_code: str):
        self.actress_calls += 1
        return ["Alice", "Bob"]

    def search_actress_works(self, actress_name: str, max_pages=None):
        self.works_calls += 1
        return [
            ActressWork(video_code="AAA-001", release_date="2020-01-01", title="t1", link="l1"),
            ActressWork(video_code="AAA-002", release_date="2020-02-01", title="t2", link="l2"),
        ]


def test_cache_tables_created(tmp_path: Path):
    db_path = tmp_path / "movie_data.db"
    cache = MovieDataCache(str(db_path))
    try:
        cur = cache.connection.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {r[0] for r in cur.fetchall()}
        assert "movie_video_actresses" in names
        assert "movie_actress_works" in names
    finally:
        cache.close()


def test_service_video_code_cache_hit(tmp_path: Path):
    svc = MovieDataCaptureService(db_path=str(tmp_path / "movie_data.db"))
    fake = _FakeClient()
    svc.client = fake
    try:
        names1 = svc.get_actress_names_by_video_code("ssis-062")
        assert names1 == ["Alice", "Bob"]
        assert fake.actress_calls == 1

        names2 = svc.get_actress_names_by_video_code("SSIS-062")
        assert names2 == ["Alice", "Bob"]
        assert fake.actress_calls == 1
    finally:
        svc.close()


def test_service_actress_works_cache_hit(tmp_path: Path):
    svc = MovieDataCaptureService(db_path=str(tmp_path / "movie_data.db"))
    fake = _FakeClient()
    svc.client = fake
    try:
        works1 = svc.get_works_by_actress_name("Some Name")
        assert len(works1) == 2
        assert fake.works_calls == 1

        works2 = svc.get_works_by_actress_name("Some Name")
        assert len(works2) == 2
        assert fake.works_calls == 1
    finally:
        svc.close()

