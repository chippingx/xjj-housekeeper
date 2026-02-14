# 交接速览（xjj-housekeeper）

面向新加入的开发者与 AI IDE：用最短时间建立对项目结构、约束与常用入口的认知。

## 项目定位

- 本地视频文件管理工具集
- 主要能力：
  - `tools/filename_formatter`：文件名清理与安全重命名（默认递归 + 扁平化输出）
  - `tools/video_info_collector`：扫描视频元数据 → CSV/SQLite 管理 → 合并/导出/查询/统计
  - `ui/`：Tkinter 桌面端（“倩影の居”），对接 `tools/` 的能力

## 必读约束

- 开发规范：[`DEVELOPMENT_GUIDELINES.md`](./DEVELOPMENT_GUIDELINES.md)
- 无迁移无兼容：[`NO_MIGRATION_POLICY.md`](./NO_MIGRATION_POLICY.md)
- 术语与命名：[`TERMINOLOGY.md`](./TERMINOLOGY.md)

## 常用入口

### 运行桌面端

```bash
python -m ui.tkinter.app
```

或使用脚本：见 `startup/`（macOS/Windows）。

### 运行工具

```bash
python -m tools.filename_formatter /path/to/videos
python -m tools.video_info_collector /path/to/videos
```

## 配置要点

- 文件名规则：
  - 用户规则文件 `rename_rules.yaml` 位于 `.gitignore`，不应提交
  - 示例：`tools/filename_formatter/rename_rules.yaml.example`
  - 可用环境变量 `RENAME_RULES_PATH` 指向用户规则文件
- 桌面端元信息：
  - `config/app_meta.json`：`version`、`release_date`、`app_name` 等

## 测试

```bash
pytest -q
```

## 代码导航建议

- 项目根定位与配置路径：`tools/path_utils.py`
- 桌面端入口与布局：`ui/tkinter/app.py`、`ui/tkinter/layout.py`
- 视频信息工具核心：`tools/video_info_collector/*`
- 文件名工具核心：`tools/filename_formatter/formatter.py`
