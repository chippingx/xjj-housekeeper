from pathlib import Path

from tools.movie_data_capture.storage import ActressWork, MovieDataStorage
from tools.movie_data_capture.service import MovieDataCaptureService


class _FakeClient:
    def __init__(self):
        self.actress_calls = 0
        self.works_calls = 0

    def get_actress_names_by_video_code(self, video_code: str):
        self.actress_calls += 1
        return ["Alice", "Bob"]

    def get_video_info(self, video_code: str):
        self.actress_calls += 1
        return {
            "video_code": video_code,
            "actresses": ["Alice", "Bob"],
            "title": "Test Title",
            "release_date": "2020-01-01",
            "link": "http://example.com"
        }

    def search_actress_works(self, actress_name: str, max_pages=None, stop_if_exists_func=None, check_cancellation=None):
        self.works_calls += 1
        all_works = [
            ActressWork(video_code="AAA-001", release_date="2020-01-01", title="t1", link="l1"),
            ActressWork(video_code="AAA-002", release_date="2020-02-01", title="t2", link="l2"),
        ]
        if stop_if_exists_func:
            filtered = []
            for w in all_works:
                if stop_if_exists_func(w.video_code):
                    break
                filtered.append(w)
            return filtered
        return all_works


def test_service_video_code_cache_hit(tmp_path: Path):
    svc = MovieDataCaptureService(db_path=str(tmp_path / "movie_data.db"))
    fake = _FakeClient()
    svc.client = fake
    try:
        names1 = svc.get_actress_names_by_video_code("tst-001")
        assert names1 == ["Alice", "Bob"]
        assert fake.actress_calls == 1

        names2 = svc.get_actress_names_by_video_code("TST-001")
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

        # Second call should use cache (no new fetch if logic works, but implementation logic is:
        # if cache exists, fetch ONLY new. So it DOES call client.search_actress_works)
        # Wait, the logic in service.py line 73: if not force_refresh and cached_works:
        # It DOES call client.search_actress_works with stop_check.
        # So fake.works_calls should increment.
        works2 = svc.get_works_by_actress_name("Some Name")
        assert len(works2) == 2
        assert fake.works_calls == 2
    finally:
        svc.close()


def test_search_movie_info_fuzzy(tmp_path: Path):
    svc = MovieDataCaptureService(db_path=str(tmp_path / "movie_data.db"))
    
    # Pre-populate DB
    svc.storage.add_video_actress_relationship(
        video_code="ABC-123",
        actress_name="Alice Wonderland",
        source="test",
        title="Alice in Wonderland",
        release_date="2022-01-01"
    )
    svc.storage.add_video_actress_relationship(
        video_code="XYZ-999",
        actress_name="Bob Builder",
        source="test",
        title="Bob's Big Adventure",
        release_date="2022-02-01"
    )
    
    # Test fuzzy search by video code part
    results = svc.search_movie_info("ABC", "all")
    assert len(results) == 1
    assert results[0].video_code == "ABC-123"
    assert results[0].title == "Alice in Wonderland"

    # Test fuzzy search by actress name part
    results = svc.search_movie_info("Builder", "all")
    assert len(results) == 1
    assert results[0].actress_name == "Bob Builder"
    
    # Test sort order (release date desc)
    # Add another one for Alice with newer date
    svc.storage.add_video_actress_relationship(
        video_code="ABC-124",
        actress_name="Alice Wonderland",
        source="test",
        title="Alice Returns",
        release_date="2023-01-01"
    )
    
    results = svc.search_movie_info("Alice", "all")
    assert len(results) == 2
    assert results[0].video_code == "ABC-124" # Newer first
    assert results[1].video_code == "ABC-123"
    
    svc.close()


def test_import_export_movie_info_file(tmp_path: Path):
    svc = MovieDataCaptureService(db_path=str(tmp_path / "movie_data.db"))
    try:
        import_file = tmp_path / "import.txt"
        import_file.write_text(
            "\n".join(
                [
                    "actress_name|video_code|release_date|title",
                    "Alice|AAA-001|2023-01-01|Title A",
                    "||2023-02-01|Title B",
                    "Bob|BBB-002|2023-13-01|Title C",
                    "Cara|CCC-003||",
                ]
            ),
            encoding="utf-8",
        )
        result = svc.import_movie_info_file(str(import_file))
        assert result["total"] == 4
        assert result["imported"] == 2
        assert result["skipped"] == 2
        assert result["invalid_date"] == 1

        export_file = tmp_path / "export.csv"
        export_result = svc.export_movie_info_file(str(export_file))
        assert export_result["total"] == 2
        content = export_file.read_text(encoding="utf-8").splitlines()
        assert content[0] == "actress_name|video_code|release_date|title"
        assert any("Alice|AAA-001|2023-01-01|Title A" in line for line in content[1:])
        assert any("Cara|CCC-003||" in line for line in content[1:])
    finally:
        svc.close()
