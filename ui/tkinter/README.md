# XJJ Housekeeper 桌面客户端（Tkinter）

该目录为新的独立桌面客户端实现，采用 Python 内置的 Tkinter，无需 Streamlit。

## 运行

- 方式一：直接运行脚本

```bash
python ui/tkinter/app.py
```

- 方式二：通过模块运行（ui 现已声明为包）

```bash
python -m ui.tkinter.app
```

## 功能

- 左侧菜单：查询、维护
- 查询页：输入关键词，调用 `ui.services.search_videos`，以表格展示结果
- 维护页：选择扫描目录并调用 `ui.services.start_maintain`，弹窗展示结果

## 注意

- 本目录与 `ui/streamlit/` 并行存在，未删除 Streamlit 代码。
- 首次运行如遇服务导入失败，请先确保 `tools/video_info_collector` 相关模块可导入并已初始化数据库路径。