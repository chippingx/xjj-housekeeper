from tools.filename_formatter.formatter import load_rules_config, save_rules_config


def test_rules_config_roundtrip(tmp_path):
    path = tmp_path / "rename_rules.yaml"
    rules = [
        {"pattern": "site@", "replace": ""},
        {"pattern": "abc_", "replace": "ABC-"},
    ]
    settings = {"video_extensions": [".mp4"], "min_file_size_bytes": 1}

    assert save_rules_config(path, rules, settings)
    loaded_rules, loaded_settings = load_rules_config(path)

    assert loaded_rules == rules
    assert loaded_settings == settings


def test_rules_config_save_filters_empty_patterns(tmp_path):
    path = tmp_path / "rename_rules.yaml"
    rules = [
        {"pattern": "   ", "replace": "x"},
        {"pattern": "ok"},
    ]

    assert save_rules_config(path, rules, {})
    loaded_rules, loaded_settings = load_rules_config(path)

    assert loaded_rules == [{"pattern": "ok", "replace": ""}]
    assert loaded_settings.get("video_extensions") == [".mp4", ".mkv", ".mov"]
