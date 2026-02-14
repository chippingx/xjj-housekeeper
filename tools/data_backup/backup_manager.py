from __future__ import annotations

import base64
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from tools.filename_formatter.formatter import load_rules_config, save_rules_config
from tools.path_utils import get_config_path
from ui.app_settings import AppSettings
from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.cli import get_default_paths

BACKUP_FORMAT_VERSION = 1


def get_default_backup_paths() -> dict[str, Path]:
    default_paths = get_default_paths()
    db_path = Path(default_paths["default_database"])
    settings_path = Path(get_config_path("output/video_info_collector/settings.json", calling_file=__file__))
    rename_rules_path = Path(get_config_path("output/video_info_collector/conf/rename_rules.yaml", calling_file=__file__))
    return {
        "db_path": db_path,
        "settings_path": settings_path,
        "rename_rules_path": rename_rules_path,
    }


def export_backup(
    backup_path: Path | str,
    db_path: Path | str | None = None,
    settings_path: Path | str | None = None,
    rename_rules_path: Path | str | None = None,
    app_version: str | None = None,
) -> dict[str, Any]:
    paths = get_default_backup_paths()
    db_path = Path(db_path) if db_path else paths["db_path"]
    settings_path = Path(settings_path) if settings_path else paths["settings_path"]
    rename_rules_path = Path(rename_rules_path) if rename_rules_path else paths["rename_rules_path"]
    backup_path = Path(backup_path)

    database_payload = _export_sqlite_database(db_path)
    settings_payload = _read_json_file(settings_path)
    rename_rules, rename_settings = load_rules_config(rename_rules_path)
    rename_payload = {"settings": rename_settings, "rename_rules": rename_rules}

    payload = {
        "format_version": BACKUP_FORMAT_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": app_version,
        "data": {
            "database": database_payload,
            "settings": settings_payload,
            "rename_rules": rename_payload,
        },
    }

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {
        "backup_path": str(backup_path),
        "table_count": len(database_payload.get("tables", [])),
        "settings_keys": len(settings_payload.keys()),
        "rename_rules_count": len(rename_rules),
    }


def import_backup(
    backup_path: Path | str,
    db_path: Path | str | None = None,
    settings_path: Path | str | None = None,
    rename_rules_path: Path | str | None = None,
    allow_newer: bool = False,
) -> dict[str, Any]:
    backup_path = Path(backup_path)
    with open(backup_path, "r", encoding="utf-8") as f:
        payload = json.load(f) or {}

    format_version = int(payload.get("format_version", 0) or 0)
    if format_version > BACKUP_FORMAT_VERSION and not allow_newer:
        raise ValueError(f"Unsupported backup version: {format_version}")

    data = payload.get("data", {}) or {}
    database_payload = data.get("database", {}) or {}
    settings_payload = data.get("settings", {}) or {}
    rename_payload = data.get("rename_rules", {}) or {}

    paths = get_default_backup_paths()
    db_path = Path(db_path) if db_path else paths["db_path"]
    settings_path = Path(settings_path) if settings_path else paths["settings_path"]
    rename_rules_path = Path(rename_rules_path) if rename_rules_path else paths["rename_rules_path"]

    _write_json_file(settings_path, settings_payload)

    rename_rules = _normalize_rules(rename_payload.get("rename_rules", []) or [])
    rename_settings = rename_payload.get("settings", {}) or {}
    save_rules_config(rename_rules_path, rename_rules, rename_settings)

    db_restored = _import_sqlite_database(db_path, database_payload)

    return {
        "backup_path": str(backup_path),
        "table_count": len(database_payload.get("tables", [])),
        "settings_keys": len(settings_payload.keys()),
        "rename_rules_count": len(rename_rules),
        "db_restored": db_restored,
    }


def initialize_data(
    reset_database: bool = True,
    reset_settings: bool = True,
    reset_rename_rules: bool = True,
    db_path: Path | str | None = None,
    settings_path: Path | str | None = None,
    rename_rules_path: Path | str | None = None,
    default_rules_path: Path | str | None = None,
) -> dict[str, Any]:
    paths = get_default_backup_paths()
    db_path = Path(db_path) if db_path else paths["db_path"]
    settings_path = Path(settings_path) if settings_path else paths["settings_path"]
    rename_rules_path = Path(rename_rules_path) if rename_rules_path else paths["rename_rules_path"]
    result = {"db_cleared": False, "settings_reset": False, "rules_reset": False}
    if reset_database:
        if db_path.exists():
            db_path.unlink()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        storage = SQLiteStorage(str(db_path))
        storage.close()
        result["db_cleared"] = True
    if reset_settings:
        settings = json.loads(json.dumps(AppSettings.DEFAULT_SETTINGS, ensure_ascii=False))
        _write_json_file(settings_path, settings)
        result["settings_reset"] = True
    if reset_rename_rules:
        rules_path = Path(default_rules_path) if default_rules_path else Path(get_config_path("tools/filename_formatter/rename_rules.yaml", calling_file=__file__))
        _, rule_settings = load_rules_config(rules_path)
        save_rules_config(rename_rules_path, [], rule_settings)
        result["rules_reset"] = True
    return result


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _export_sqlite_database(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"path": str(db_path), "tables": [], "schema_objects": []}
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    schema_objects = _load_schema_objects(cursor)
    table_names = [obj["name"] for obj in schema_objects if obj["type"] == "table"]
    tables = []
    for table in table_names:
        columns = _load_table_columns(cursor, table)
        rows = cursor.execute(f'SELECT * FROM "{table}"').fetchall()
        data_rows = [_normalize_row(dict(row), columns) for row in rows]
        create_sql = next((obj["sql"] for obj in schema_objects if obj["type"] == "table" and obj["name"] == table), None)
        tables.append(
            {
                "name": table,
                "create_sql": create_sql,
                "columns": columns,
                "rows": data_rows,
            }
        )
    connection.close()
    return {
        "path": str(db_path),
        "tables": tables,
        "schema_objects": schema_objects,
    }


def _import_sqlite_database(db_path: Path, payload: dict[str, Any]) -> bool:
    tables = payload.get("tables", []) or []
    schema_objects = payload.get("schema_objects", []) or []
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    _drop_existing_objects(cursor)
    for table in tables:
        create_sql = table.get("create_sql")
        if create_sql:
            cursor.execute(create_sql)
    for table in tables:
        _insert_table_rows(cursor, table)
    for obj in schema_objects:
        if obj.get("type") in {"index", "trigger", "view"} and obj.get("sql"):
            cursor.execute(obj["sql"])
    connection.commit()
    connection.close()
    return True


def _drop_existing_objects(cursor: sqlite3.Cursor) -> None:
    existing = cursor.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for obj_type, name in existing:
        cursor.execute(f'DROP {obj_type.upper()} IF EXISTS "{name}"')


def _load_schema_objects(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    rows = cursor.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [
        {"type": row["type"], "name": row["name"], "tbl_name": row["tbl_name"], "sql": row["sql"]}
        for row in rows
    ]


def _load_table_columns(cursor: sqlite3.Cursor, table: str) -> list[str]:
    info = cursor.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [row[1] for row in info]


def _insert_table_rows(cursor: sqlite3.Cursor, table: dict[str, Any]) -> None:
    name = table.get("name")
    columns = list(table.get("columns", []) or [])
    rows = table.get("rows", []) or []
    if not name or not columns or not rows:
        return
    column_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [_denormalize_row(row, columns) for row in rows]
    cursor.executemany(f'INSERT INTO "{name}" ({column_sql}) VALUES ({placeholders})', values)


def _normalize_row(row: dict[str, Any], columns: Iterable[str]) -> dict[str, Any]:
    normalized = {}
    for col in columns:
        normalized[col] = _normalize_value(row.get(col))
    return normalized


def _denormalize_row(row: dict[str, Any], columns: Iterable[str]) -> list[Any]:
    values = []
    for col in columns:
        values.append(_denormalize_value(row.get(col)))
    return values


def _normalize_value(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        encoded = base64.b64encode(bytes(value)).decode("utf-8")
        return {"__base64__": encoded}
    return value


def _denormalize_value(value: Any) -> Any:
    if isinstance(value, dict) and "__base64__" in value:
        return base64.b64decode(value["__base64__"])
    return value


def _normalize_rules(rules: Iterable[dict]) -> list[dict]:
    normalized: dict[str, dict] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        pattern = str(rule.get("pattern", "")).strip()
        if not pattern:
            continue
        replace = rule.get("replace", "")
        if pattern in normalized:
            del normalized[pattern]
        normalized[pattern] = {"pattern": pattern, "replace": "" if replace is None else str(replace)}
    return list(normalized.values())
