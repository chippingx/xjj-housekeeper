# UI 模块文档

## 概述

UI 模块是 XJJ Housekeeper 的本地界面层，目前以 Tkinter 为主实现（桌面客户端）。

- 桌面版（Tkinter）入口：`ui/tkinter/app.py`

## 技术栈

- Python 3.10+
- Tkinter（桌面原生）
- SQLite3（本地数据库，路径见下文）
- 业务能力沿用 `tools/video_info_collector` 模块

## 目录结构（当前）

```
ui/
├── README.md
├── app_settings.py        # 应用设置（持久化到 output/*）
├── services.py            # 业务服务（查询/维护，对接 tools/video_info_collector）
└── tkinter/               # Tkinter 桌面实现
    ├── app.py
    ├── README.md
    └── implementation-logs.md
```

## 文件说明

1) `services.py`
- 职责：封装数据库访问与扫描/维护逻辑（调用 `tools/video_info_collector`）
- 关键点：
  - `search_videos(keyword)`：空字符串返回空结果；优先按 `video_code` 模糊匹配，不存在该列时回退到 `filename/file_path` 模糊匹配；文件大小格式化为 `G/M`
  - `start_maintain(path, labels, logical_path)`：调用增强扫描；当找到 0 个可处理文件时，当前实现返回“成功（空结果）”的提示摘要
  - 默认数据库路径：`output/video_info_collector/database/video_database.db`（如不存在会自动创建父目录）

2) `app_settings.py`
- 职责：保存 UI 偏好设置（例如每页数量、可见列）

3) `tkinter/app.py`
- 职责：Tkinter 桌面客户端入口（查询/维护）

## 已实现功能（基于当前代码）

- 桌面版（Tkinter）
  - 顶部水平导航（查询/维护）
  - 查询页：基于 `video_code` 的模糊匹配，输入即搜；双击“路径”打开所在目录，其它列双击用默认播放器播放视频；右键可选择播放器
  - 维护页：真实进度条、日志区域、完成摘要

## 运行与启动

- 桌面版（Tkinter）
```bash
python ui/tkinter/app.py
# 或
python -m ui.tkinter.app
```

## 注意事项

- Python >= 3.10；依赖管理使用项目根的 `pyproject.toml`
- 默认数据库路径需存在父目录：`output/video_info_collector/database/`
- macOS 特性：首次使用目录/文件访问可能需要授权

## 相关文档

- 项目主 README：`../README.md`
- 设计文档：`ui/design/design.md`、`ui/design/design_system.md`
- 术语表：`../TERMINOLOGY.md`
- 开发指南：`../DEVELOPMENT_GUIDELINES.md`
