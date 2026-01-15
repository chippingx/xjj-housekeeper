from tools.movie_data_capture.cli import main as cli_main


class _FakeService:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def close(self):
        return None

    def get_actress_names_by_video_code(self, video_code: str, force_refresh: bool = False):
        if video_code.upper() == "TST-001":
            return ["A1", "A2"]
        return []

    def get_works_by_actress_name(self, actress_name: str, force_refresh: bool = False, max_pages=None):
        class _W:
            def __init__(self, code, date, title):
                self.video_code = code
                self.release_date = date
                self.title = title
                self.link = None

        if actress_name == "X":
            return [_W("AAA-001", "2020-01-01", "t1")]
        return []


def test_cli_by_code(monkeypatch, capsys):
    import tools.movie_data_capture.cli as cli_mod

    monkeypatch.setattr(cli_mod, "MovieDataCaptureService", _FakeService)
    code = cli_main(["--database", ":memory:", "by-code", "TST-001"])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "A1, A2"


def test_cli_by_actress(monkeypatch, capsys):
    import tools.movie_data_capture.cli as cli_mod

    monkeypatch.setattr(cli_mod, "MovieDataCaptureService", _FakeService)
    code = cli_main(["--database", ":memory:", "by-actress", "X"])
    out = capsys.readouterr().out
    assert code == 0
    assert "AAA-001" in out

