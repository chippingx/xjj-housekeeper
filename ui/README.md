# UI 模块（Tkinter 桌面端）

UI 模块提供本地桌面端界面（当前为 Tkinter 实现），用于在本机对视频库进行查询、维护与设置。桌面端主要复用 `tools/video_info_collector` 的数据库与业务能力。

## 启动方式

```bash
python -m ui.tkinter.app
```

也可以使用 `startup/` 下的脚本启动或打包（macOS/Windows）。

## 数据与配置

- 默认数据库：`output/video_info_collector/database/video_database.db`
- UI 设置：`output/video_info_collector/settings.json`
- 应用元信息：`config/app_meta.json`（版本号、发布日期、应用名等）

## 目录结构

```
ui/
├── services.py          业务服务封装（对接 tools/video_info_collector）
├── app_settings.py      UI 设置持久化
└── tkinter/             Tkinter 实现
    ├── app.py           桌面端入口
    ├── layout.py        主布局与 About 弹窗
    ├── query_page.py    查询页
    └── maintain_*       维护页与设置页
```

## 已实现功能（以当前代码为准）

- 侧边栏导航：查询 / 维护
- 查询页：
  - 关键词搜索（支持按 `video_code` / 文件名 / 路径等字段查询）
  - 标签搜索（基于 `video_tags`）
  - 分页、排序、可见列配置
  - 双击路径打开文件管理器；双击其它列播放视频（可选播放器）
  - 偏好标记（like/dislike/deleted/none）
- 维护页：
  - 扫描目录并写入数据库
  - 问题视频工具（损坏/重复等）
  - 数据备份与恢复
  - 影视资讯导入/查询（当对应服务可用时）

## 相关开发约束

- 开发规范与 AI 准则：`../doc/DEVELOPMENT_GUIDELINES.md`
- 无迁移无兼容政策：`../doc/NO_MIGRATION_POLICY.md`
- 术语表：`../doc/TERMINOLOGY.md`
