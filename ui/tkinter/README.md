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

- 顶部水平导航：查询、维护
- 查询页：基于视频 code 的模糊搜索，支持“输入即搜”
  - 每输入一个字符即进行实时匹配
  - 首列显示“视频”（优先显示视频 code，缺省回退文件名）
  - 路径列显示视频所在目录（非完整文件路径）
- 维护页：选择扫描目录并调用 `ui.services.start_maintain`，页面内显示进度与摘要

## 注意

- 本目录与 `ui/streamlit/` 并行存在，未删除 Streamlit 代码。
-- 首次运行如遇服务导入失败，请先确保 `tools/video_info_collector` 相关模块可导入并已初始化数据库路径。

## 设计说明（查询页）

- 搜索依据：视频 code（`video_code` 列），模糊匹配（`LIKE '%keyword%'`）
- 兼容性：若数据库暂缺 `video_code` 列，则回退按文件名/路径模糊匹配
- 表格列：`视频 | 路径 | 大小 | 时长 | 分辨率`
- 行操作：
  - 双击“路径”列打开所在目录
  - 双击其他列直接播放视频（使用真实 `file_path`，避免 code 与文件名不一致导致失败）