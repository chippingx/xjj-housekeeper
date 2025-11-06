# xjj_housekeeper

本地视频文件整理与信息管理工具集，包含「文件名规范化」与「视频信息收集」两大子工具。项目内置测试与提交钩子，遵循“无迁移无兼容政策”，保证代码质量与简单架构。

## 工具

- 文件名规范化工具（`tools/filename_formatter`）
  - 批量规范化/重命名视频文件名（例如将 123ABC.mp4 → ABC-123.mp4）
  - 默认扁平化输出到根目录，支持预览模式、冲突自动重命名与操作日志
  - 规则通过 YAML 配置（`tools/filename_formatter/rename_rules.yaml`），支持环境变量覆盖
  - 详细说明：`tools/filename_formatter/README.md`

- 视频信息收集工具（`tools/video_info_collector`）
  - 批量收集视频元数据（文件名、相对路径、大小、时长、创建时间）并支持标签与逻辑路径
  - 两阶段工作流：临时 CSV 收集 → 合并到 SQLite 主数据库；支持导出/查询/统计
  - 适用于大规模视频库管理与后续数据分析
  - 详细说明：`tools/video_info_collector/README.md`

## 快速开始

- 环境要求：
  - Python 3.10+
  - 推荐安装 `ffmpeg`（用于提取视频时长等元数据）
  - 可选安装 `sqlite3`（用于本地查看数据库文件）

- 安装依赖：
  - Poetry：`poetry install`
  - 或 pip：`pip install -r requirements.txt`

- 安装提交钩子：
  - 在项目根目录执行：`./setup_hooks.sh`
  - 该钩子在提交前自动检查是否有违反“无迁移无兼容政策”的代码

## 命令用法

- 文件名规范化（filename_formatter）：
  - 基本用法：`python -m tools.filename_formatter <目录路径>`
  - 预览模式：`python -m tools.filename_formatter <目录路径> --dry-run`
  - 冲突自动重命名：`python -m tools.filename_formatter <目录路径> --conflict-resolution rename`
  - 更多参数与示例见 `tools/filename_formatter/README.md`

- 视频信息收集（video_info_collector）：
  - 收集到临时 CSV：`python -m tools.video_info_collector /path/to/videos`
  - 添加标签/逻辑路径：`python -m tools.video_info_collector /path/to/videos --tags "动作片;高清" --path "电影/动作片/2024"`
  - 指定扩展名与递归：`python -m tools.video_info_collector /path/to/videos --extensions .mp4,.mkv --recursive`
  - 合并到主库：`python -m tools.video_info_collector --merge temp_collection.csv --database output/video_info_collector/database/video_database.db --duplicate-strategy update`
  - 导出为 CSV：`python -m tools.video_info_collector --export output/video_info_collector/database/video_database.db --format csv --output output/video_info_collector/csv/exported_data.csv`
  - 通过视频code查询：`python -m tools.video_info_collector --search-video-code "ABC-123,DEF-456"`
  - 统计信息：`python -m tools.video_info_collector stats --type basic`
  - 完整用法见 `tools/video_info_collector/README.md`

### 示例输出（文件名规范化）

```
处理目录: /path/to/videos
处理扩展名: .mp4, .mkv, .mov
最小文件大小: 104857600 字节
使用规则文件: tools/filename_formatter/rename_rules.yaml
递归子目录: 是
扁平化输出: 是（默认）

success: /path/to/videos/sub/ABC123.mp4 -> /path/to/videos/ABC-123.mp4
success: /path/to/videos/sub2/DEF456ch.mp4 -> /path/to/videos/DEF-456.mp4
skipped: same name: /path/to/videos/TST-001.mp4 -> /path/to/videos/TST-001.mp4
would skip: target exists: /path/to/videos/sub/ABC-123.mp4 -> /path/to/videos/ABC-123.mp4

统计:
- 总计: 4
- 成功: 2
- 跳过(目标已存在): 1
- 跳过(同名): 1
- 失败: 0
```

## 项目结构

- `tools/filename_formatter/` - 文件名规范化工具与 `rename_rules.yaml`
- `tools/video_info_collector/` - 视频信息收集工具（扫描、合并、查询、统计）
- `tests/` - 测试用例（两大子工具均有覆盖）
- `.githooks/pre-commit` - 提交前检查脚本
- `setup_hooks.sh` - 安装 Git 钩子的脚本
- `NO_MIGRATION_POLICY.md` - 无迁移无兼容政策说明

## 无迁移无兼容政策

- 项目严格禁止迁移和向后兼容代码路径，保持架构简洁。
- 允许只读的结构自检与信息查询（例如测试中的 `PRAGMA table_info`）。
- 如需修改数据库结构，直接在创建函数中定义完整结构并重建数据库。
- 详情见 `NO_MIGRATION_POLICY.md`。

## 测试

- 运行全部测试：`pytest -q`
- 仅运行视频信息收集工具相关测试：`python -m pytest tests/tool_video_info_collector/ -q`

## 路线图（Roadmap）

- 已完成：
  - 文件名规范化工具：规则驱动、预览、安全重命名、扁平化输出
  - 视频信息收集工具：临时收集、合并主库、查询、统计、导出
  - 提交钩子与政策文档：安装脚本与违规拦截

- 已完成：
  - Streamlit桌面应用（基于PyWebView）
  - 启动脚本统一管理（startup目录）

- 计划中：
  - 更丰富的统计报表与图表导出
  - 批量数据导入/导出的增强

## 桌面应用

项目提供基于Streamlit + PyWebView的桌面应用，提供独立的桌面窗口体验。

### 快速启动
```bash
# 推荐方式：浏览器版本（最稳定）
./startup/start-desktop.sh  # Linux/macOS
startup/start-desktop.bat  # Windows

# 桌面窗口版本（实验性）
./startup/run-streamlit-desktop.sh  # Linux/macOS
startup/run-streamlit-desktop.bat  # Windows
```

详细说明请参考：[桌面应用文档](startup/README_DESKTOP.md)

## 常见问题

- 为什么提交被阻止？
  - 可能包含迁移/兼容相关代码。执行 `./setup_hooks.sh` 以安装钩子，并参考 `NO_MIGRATION_POLICY.md` 清理相关代码。
- 如何修改文件重命名规则？
  - 编辑 `tools/filename_formatter/rename_rules.yaml` 或设置环境变量 `RENAME_RULES_PATH` 指向自定义配置。
- 如何查看/分析主数据库？
  - 使用浏览器 SQLite 插件或命令行工具 `sqlite3`，也可通过导出为 CSV 分析。