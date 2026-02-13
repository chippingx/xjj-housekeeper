import json
from pathlib import Path


class I18n:
    def __init__(self, i18n_dir: Path, language: str, fallback: str = "zh_CN"):
        self.i18n_dir = i18n_dir
        self.language = language or fallback
        self.fallback = fallback
        self._translations: dict[str, dict] = {}
        self._load_language(self.language)
        if self.fallback != self.language:
            self._load_language(self.fallback)

    def _load_language(self, lang: str):
        if lang in self._translations:
            return
        path = self.i18n_dir / f"{lang}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._translations[lang] = json.load(f) or {}
        except Exception:
            self._translations[lang] = {}

    def t(self, key: str, default: str | None = None, **kwargs):
        data = self._translations.get(self.language, {})
        fallback = self._translations.get(self.fallback, {})
        if key in data:
            value = data[key]
        elif key in fallback:
            value = fallback[key]
        else:
            value = default if default is not None else key
        try:
            return str(value).format(**kwargs)
        except Exception:
            return str(value)
