# Video Info Collector

本工具用于扫描本地视频文件并收集元数据，支持输出 CSV 或写入 SQLite 数据库；并提供“合并 CSV → 主库”、导出、按视频号查询与统计等能力。核心目标是可复用的“视频库清单”能力，供 CLI 与桌面端共同使用。

## 依赖

- Python 3.10+
- 系统依赖：FFmpeg（需要 `ffprobe`）
  - macOS：`brew install ffmpeg`
- SQLite：Python 标准库自带驱动；数据库文件位于 `output/` 下

## 快速开始

### 1) 扫描目录（默认输出 CSV）

```bash
python -m tools.video_info_collector /path/to/videos
```

常用参数：
- `--tags "动作片;高清;2024"`：为本次扫描结果统一附加标签（分号分隔）
- `--path "电影/动作片/2024"`：为本次扫描结果统一设置逻辑路径
- `--extensions .mp4,.mkv,.avi`：扩展名过滤
- `--output-format {csv,sqlite}`：输出格式（默认 `csv`）
- `--output <文件路径>`：指定输出文件（CSV 或 SQLite）
- `--dry-run`：预览模式（不写入 CSV/DB）

默认输出目录（会自动创建）：
- `output/video_info_collector/csv/`
- `output/video_info_collector/database/video_database.db`

### 2) 合并 CSV 到主数据库

```bash
python -m tools.video_info_collector --merge /path/to/temp.csv
```

可选参数：
- `--database <db路径>`：指定主库路径
- `--duplicate-strategy {skip,update,append}`：重复项处理策略（默认 `skip`）
- `--force`：强制重新合并已合并过的 CSV

### 3) 导出数据库

```bash
python -m tools.video_info_collector --export /path/to/video_database.db --output exported.csv
python -m tools.video_info_collector --export /path/to/video_database.db --format json --output exported.json
python -m tools.video_info_collector --export-simple /path/to/video_database.db --output simple.txt
```

### 4) 查询（按视频号）

```bash
python -m tools.video_info_collector --search-video-code "ABC-123,DEF-456"
```

支持逗号或空格分隔多个 `video_code`。

### 5) 统计

```bash
python -m tools.video_info_collector --stats
python -m tools.video_info_collector --stats --group-by tags
python -m tools.video_info_collector --stats --group-by resolution
python -m tools.video_info_collector --stats --group-by duration
```

### 6) 初始化/重置数据库

```bash
python -m tools.video_info_collector --init-db
```

该操作会清空目标数据库中的数据（用于开发/测试或结构调整后的重建）。

## 数据库结构（当前实现）

SQLite 由 [`sqlite_storage.py`](./sqlite_storage.py) 创建数据表，核心表包括：

- `video_info`：视频主表（路径、文件名、时长、分辨率、`video_code`、`file_status` 等）
- `video_tags`：多标签表（`video_id` + `tag`）
- `scan_history`：扫描历史摘要
- `video_master_list`：按 `video_code` 的全局视角主列表
- `merge_history`：合并/变更事件记录
- `video_preferences`：用户偏好（like/dislike/deleted/none 等）
- `movie_actress_works`：影视资讯数据（可选能力）

## 安全性说明

- 扫描阶段对视频文件为只读访问，不修改原始视频文件
- 写入仅发生在 `output/` 下的 CSV/SQLite 等输出文件
- 所有数据库写入使用参数化查询，避免 SQL 注入
