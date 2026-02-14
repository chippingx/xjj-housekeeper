# 开发纲要（高层视角）

本文件描述项目的高层结构与边界，避免写入易过期的实现细节。具体开发约束见 [`DEVELOPMENT_GUIDELINES.md`](./DEVELOPMENT_GUIDELINES.md)。

## 目标

- 为本地视频文件提供整理、扫描、信息管理与桌面端操作能力
- 核心优先级：安全（不覆盖/不删除）与可验证（测试覆盖）

## 代码结构

```
xjj-housekeeper/
├── tools/                 工具与可复用能力
│   ├── filename_formatter 文件名清理与安全重命名
│   ├── video_info_collector 视频扫描/存储/合并/导出/查询
│   ├── data_backup        数据备份（面向桌面端）
│   └── movie_data_capture 影视资讯抓取/存储（可选能力）
├── ui/                    桌面端（Tkinter）
├── startup/               启动与打包脚本
├── config/                应用元信息（例如 app_meta.json）
├── doc/                   长期开发文档（本目录）
└── tests/                 测试套件
```

## 关键约束

- 无迁移无兼容：见 [`NO_MIGRATION_POLICY.md`](./NO_MIGRATION_POLICY.md)
- 命名与字段：见 [`TERMINOLOGY.md`](./TERMINOLOGY.md)
- 变更必须可验证：任何代码修改后需跑 `pytest -q`

## 版本与发布（约定）

- `pyproject.toml`：Python 包版本与依赖声明
- `config/app_meta.json`：桌面端展示的版本/发布日期/应用名等元信息
- `XJJ-Housekeeper.spec`：macOS `.app` 的打包配置（含版本写入）
