# UI 模块文档

## 概述

UI 模块是 XJJ Housekeeper 的本地界面层，目前以 Tkinter 为主实现（桌面客户端），Streamlit 代码仅用于早期样式验证，后续将移除。

- Web（Streamlit）主入口：`ui/app.py`
- 桌面版（Tkinter）入口：`ui/tkinter/app.py`
- 另有一套并行的 Streamlit 实现位于 `ui/streamlit/`，用于分层与样式验证（不作为默认入口）。

## 技术栈

- Python 3.10+
- Streamlit 1.39+
- Tkinter（桌面原生）
- SQLite3（本地数据库，路径见下文）
- 业务能力沿用 `tools/video_info_collector` 模块

## 目录结构（当前）

```
ui/
├── README.md
├── app.py                 # Streamlit 主入口（当前实际运行入口）
├── services.py            # 业务服务（Streamlit 入口使用此文件）
├── table_renderer.py      # 结果表格渲染（HTML）
├── validation.py          # 查询输入校验（精确匹配）
├── maintain_form.py       # 维护页样式/脚本片段（仅样式与静态片段）
├── streamlit/             # 并行的 Streamlit 实现（包含同名文件，供验证/比对）
└── tkinter/               # Tkinter 桌面实现
    ├── app.py
    ├── README.md
    └── implementation-logs.md
```

## 文件说明（基于当前入口 ui/app.py 与同目录实现）

1) `app.py`（Streamlit 主入口）
- 职责：页面路由（查询/维护）、状态管理、布局与交互
- 行为：
  - 查询页：文本框输入变化即触发查询尝试；仅当输入通过校验（精确格式）时显示结果
  - 维护页：支持通过系统对话框选择目录（macOS 采用子进程隔离 Tkinter 方案），并显示执行结果摘要

2) `services.py`
- 职责：封装数据库访问与扫描/维护逻辑（调用 `tools/video_info_collector`）
- 关键点：
  - `search_videos(keyword)`：空字符串返回空结果；优先按 `video_code` 模糊匹配，不存在该列时回退到 `filename/file_path` 模糊匹配；文件大小格式化为 `G/M`
  - `start_maintain(path, labels, logical_path)`：调用增强扫描；当找到 0 个可处理文件时，当前实现返回“成功（空结果）”的提示摘要
  - 默认数据库路径：`output/video_info_collector/database/video_database.db`（如不存在会自动创建父目录）

3) `table_renderer.py`
- 职责：将服务层返回的行数据渲染为 HTML 表格
- 列：`视频 | 大小 | 路径`，`视频/大小` 不换行，`路径` 可换行（break-all）

4) `validation.py`
- 职责：查询输入校验
- 规则：仅允许精确匹配的视频编号格式（示例：`ABC-123`），禁止空/通配符（`*`/`?`）

5) `maintain_form.py`
- 职责：提供维护页所需的样式与静态脚本片段（非必需，当前入口主要使用 Streamlit 原生组件）

## 已实现功能（基于当前代码）

- 查询模式（Streamlit）
  - 精确格式校验（通过后显示结果）
  - 输入变化自动触发查询尝试（不符合格式时仅提示，不显示表格）
  - 结果表格展示、空状态/错误提示
- 维护模式（Streamlit）
  - 目录选择（macOS 采用子进程运行 Tkinter 避免崩溃）
  - 进度/结果摘要反馈（成功/错误信息友好）
- 桌面版（Tkinter）
  - 顶部水平导航（查询/维护）
  - 查询页：基于 `video_code` 的模糊匹配，输入即搜；双击“路径”打开所在目录，其它列双击用默认播放器播放视频；右键可选择播放器
  - 维护页：真实进度条、日志区域、完成摘要

## 运行与启动

- Web 版（Streamlit）
```bash
python3 -m streamlit run ui/app.py --server.port 8501
```
说明：`ui/app.py` 为实际入口；`ui/streamlit/` 目录为并行实现（非默认入口）。

- 桌面版（Tkinter）
```bash
python ui/tkinter/app.py
# 或
python -m ui.tkinter.app
```

## 注意事项

- Python >= 3.10；依赖管理使用项目根的 `pyproject.toml`
- 默认数据库路径需存在父目录：`output/video_info_collector/database/`
- 浏览器建议：Chrome 86+/Edge 86+；Safari 对 File System Access API 支持有限
- macOS 特性：首次使用目录/文件访问可能需要授权

## 已知差异/问题（与并行实现或设计说明的差异，仅罗列，不在此处改动设计文档）

- 字段命名差异：当前入口使用的 `ui/services.py` 返回字段为 `video/file_path/file_size/duration/resolution`；而 `ui/table_renderer.py` 期望 `filename/duration/resolution/...`，导致“视频”列可能为空。`ui/streamlit/services.py` 与其同目录的渲染器字段一致，不存在该问题。
- 查询策略差异：`design/design.md` 与 `ui/streamlit/validation.py` 要求“仅精确匹配，禁空/禁模糊”；当前入口的 `validation.py` 也为精确校验，但 `ui/services.py` 在 `video_code` 列缺失时会回退到 `filename/file_path` 的模糊匹配（实现层面与“仅精确匹配”的设计描述存在偏差）。
- 维护 0 结果的语义差异：`ui/services.py` 在未发现可处理文件时返回“成功（空结果）”的提示；而 `ui/streamlit/services.py` 在同情形返回失败提示。
- 导航样式差异：并行实现 `ui/streamlit/app.py` 使用侧边栏大按钮进行路由切换；当前入口页使用页内按钮与顶部栏样式更为简化。

以上差异已在本 README 标注；若需统一至设计方案，请以设计文档为准并优先调整实现代码（非本文档）。

## 相关文档

- 项目主 README：`../README.md`
- 设计文档：`ui/design/design.md`、`ui/design/design_system.md`
- 术语表：`../TERMINOLOGY.md`
- 开发指南：`../DEVELOPMENT_GUIDELINES.md`
