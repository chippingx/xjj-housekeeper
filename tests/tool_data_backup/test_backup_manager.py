import json
import sqlite3
from pathlib import Path

from tools.data_backup.backup_manager import export_backup, import_backup, initialize_data
from tools.filename_formatter.formatter import load_rules_config, save_rules_config


def _create_sample_db(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT, blob_data BLOB)")
    cursor.execute("INSERT INTO sample (name, blob_data) VALUES (?, ?)", ("alpha", b"\x00\x01"))
    connection.commit()
    connection.close()


def _read_sample_db(path: Path):
    connection = sqlite3.connect(str(path))
    cursor = connection.cursor()
    rows = cursor.execute("SELECT id, name, blob_data FROM sample ORDER BY id").fetchall()
    connection.close()
    return rows


def test_export_import_roundtrip(tmp_path: Path):
    db_path = tmp_path / "data.db"
    settings_path = tmp_path / "settings.json"
    rules_path = tmp_path / "rename_rules.yaml"
    backup_path = tmp_path / "backup.json"

    _create_sample_db(db_path)
    settings = {
        "app_title": "Test App",
        "tags": ["tag-a"],
        "page_size": 10,
        "visible_columns": ["video"],
        "language": "en_US",
    }
    settings_path.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")
    save_rules_config(
        rules_path,
        [{"pattern": "example.com_", "replace": ""}],
        {"video_extensions": [".mp4"], "min_file_size_bytes": 1},
    )

    export_backup(
        backup_path,
        db_path=db_path,
        settings_path=settings_path,
        rename_rules_path=rules_path,
        app_version="T1",
    )

    db_path.unlink()
    settings_path.unlink()
    rules_path.unlink()

    result = import_backup(
        backup_path,
        db_path=db_path,
        settings_path=settings_path,
        rename_rules_path=rules_path,
    )

    assert result["table_count"] == 1
    assert _read_sample_db(db_path) == [(1, "alpha", b"\x00\x01")]
    loaded_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert loaded_settings["app_title"] == "Test App"
    rules, rule_settings = load_rules_config(rules_path)
    assert rules[0]["pattern"] == "example.com_"
    assert rule_settings["min_file_size_bytes"] == 1


def test_import_dedupes_rules(tmp_path: Path):
    db_path = tmp_path / "data.db"
    settings_path = tmp_path / "settings.json"
    rules_path = tmp_path / "rename_rules.yaml"
    backup_path = tmp_path / "backup.json"

    payload = {
        "format_version": 1,
        "created_at": "2026-01-01T00:00:00",
        "data": {
            "database": {"tables": [], "schema_objects": []},
            "settings": {"app_title": "Dedupe Test"},
            "rename_rules": {
                "settings": {"video_extensions": [".mp4"], "min_file_size_bytes": 1},
                "rename_rules": [
                    {"pattern": "dup_", "replace": ""},
                    {"pattern": "keep_", "replace": "x"},
                    {"pattern": "dup_", "replace": "y"},
                ],
            },
        },
    }
    backup_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    import_backup(
        backup_path,
        db_path=db_path,
        settings_path=settings_path,
        rename_rules_path=rules_path,
    )

    rules, _ = load_rules_config(rules_path)
    assert len(rules) == 2
    assert rules[-1]["pattern"] == "dup_"
    assert rules[-1]["replace"] == "y"


def test_initialize_data_resets_state(tmp_path: Path):
    db_path = tmp_path / "data.db"
    settings_path = tmp_path / "settings.json"
    rules_path = tmp_path / "rename_rules.yaml"
    default_rules_path = tmp_path / "default_rules.yaml"

    _create_sample_db(db_path)
    settings_path.write_text(json.dumps({"app_title": "Custom"}, ensure_ascii=False), encoding="utf-8")
    save_rules_config(rules_path, [{"pattern": "old_", "replace": ""}], {"video_extensions": [".mp4"]})
    save_rules_config(default_rules_path, [{"pattern": "new_", "replace": ""}], {"video_extensions": [".mkv"]})

    result = initialize_data(
        db_path=db_path,
        settings_path=settings_path,
        rename_rules_path=rules_path,
        default_rules_path=default_rules_path,
    )

    assert result["db_cleared"] is True
    assert db_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["app_title"]
    rules, rule_settings = load_rules_config(rules_path)
    assert rules == []
    assert rule_settings["video_extensions"] == [".mkv"]
