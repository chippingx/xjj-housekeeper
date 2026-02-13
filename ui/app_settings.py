import json
import os
from pathlib import Path
from tools.path_utils import get_config_path

class AppSettings:
    DEFAULT_SETTINGS = {
        "app_title": "倩影の居",
        "tags": [],
        "page_size": 20,
        "visible_columns": ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"],
        "language": "zh_CN"
    }
    
    SETTINGS_FILE = str(get_config_path("output/video_info_collector/settings.json", calling_file=__file__))

    def __init__(self):
        import copy
        self._settings = copy.deepcopy(self.DEFAULT_SETTINGS)
        self.settings_file = Path("settings.json")
        self.load_settings()

    def _ensure_dir_exists(self):
        """Ensure the directory for settings file exists."""
        try:
            path = Path(self.SETTINGS_FILE)
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating settings directory: {e}")

    def _is_test_env(self):
        return os.environ.get("PYTEST_CURRENT_TEST") is not None

    def load_settings(self):
        """Load settings from JSON file. If file doesn't exist, use defaults."""
        if self._is_test_env():
            return
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Update settings with loaded data, preserving defaults for missing keys
                    self._settings.update(data)
            except Exception as e:
                print(f"Error loading settings: {e}")
        else:
            # If file doesn't exist, save the default settings
            self.save_settings()

    def save_settings(self):
        """Save current settings to JSON file."""
        if self._is_test_env():
            return
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key, value):
        """Set a setting value."""
        self._settings[key] = value

    @property
    def app_title(self):
        return self._settings.get("app_title", "倩影の居")

    @app_title.setter
    def app_title(self, value):
        self._settings["app_title"] = value

    @property
    def tags(self):
        return self._settings.get("tags", [])

    @tags.setter
    def tags(self, value):
        if isinstance(value, list):
            # Always store a copy to avoid shared reference issues
            self._settings["tags"] = list(value)

    @property
    def page_size(self):
        return self._settings.get("page_size", 20)

    @page_size.setter
    def page_size(self, value):
        try:
            self._settings["page_size"] = int(value)
        except ValueError:
            pass

    @property
    def visible_columns(self):
        default_cols = self.DEFAULT_SETTINGS["visible_columns"]
        cols = self._settings.get("visible_columns", default_cols)
        # Ensure "video" is always present
        if "video" not in cols:
            cols.insert(0, "video")
        return cols

    @visible_columns.setter
    def visible_columns(self, value):
        if isinstance(value, list):
            # Ensure "video" is always present
            if "video" not in value:
                value.insert(0, "video")
            self._settings["visible_columns"] = list(value)

    @property
    def language(self):
        return self._settings.get("language", "zh_CN")

    @language.setter
    def language(self, value):
        if value in ("zh_CN", "zh_TW", "en_US", "ja_JP", "ko_KR", "th_TH"):
            self._settings["language"] = value
        else:
            self._settings["language"] = "zh_CN"
