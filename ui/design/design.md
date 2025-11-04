# UI 设计文档（Streamlit 本地客户端）

> 版本：v0.1 草案  
> 日期：2025-11-04  
> 面向平台：macOS、Windows（跨平台，本地运行）

---

## 1. 背景与目标

- 目标：构建一个基于 Streamlit 的本地客户端，提供“扫描目录→生成并人工校验 CSV→合并入数据库→查询/统计→导出”的完整工作流可视化与可控执行，严格遵循项目的“无迁移无兼容”与文档安全规范。
- 参考流程：详见 `debug/video_info_collector/CLI_DEMO.md` 中的推荐工作流程。
- 使用场景：在本机以图形化方式管理视频信息库，无需部署远程 Web 服务，不对外暴露接口，强调安全与可控。
- 非目标：
  - 不实现远程访问或多租户；
  - 不实现数据库迁移（遵循 `NO_MIGRATION_POLICY.md`）；
  - 不绕过既有工具的安全与检查策略（如 hooks）。

## 2. 技术栈与运行模式

- 技术栈：
  - 前端/UI：当前阶段以 `ui/design` 下的高保真静态页面为单一信源；生成页面代码时再选择具体框架（建议 Streamlit 或本地前端 + Python 服务），严格按设计系统与高保真映射实现。
  - 后端/数据：沿用 `tools/video_info_collector` 与 SQLite；UI 层的调用接口在生成阶段通过轻薄 `services` 封装。
  - 封装：`services` 层在生成阶段落地，负责与现有 Python 模块或 CLI 对接。
- 运行模式：
  - 当前阶段：本地浏览器直接打开 `ui/design` 下的高保真静态页进行预览与评审。
  - 生成阶段：本地单机 UI（框架待定），仅绑定 `localhost`；不暴露到外网；所有文件读写基于本机路径与既有约定。
- 跨平台策略：
  - 路径与分隔符兼容（`os.path`/`pathlib`）；
  - 依赖检测（FFmpeg/ffprobe、SQLite）并提供友好提示；
  - Windows 与 macOS 下统一的入口与配置体验。

## 3. 架构与目录规划（当前设计产物）

```
ui/
└── design/
    ├── index.html                             # 交互原型（查询 ↔ 维护入口）
    ├── hifi-desktop.html                      # 查询页（桌面 1440×900）
    ├── hifi-mobile.html                       # 查询页（移动 375×667）
    ├── hifi-desktop-maintain.html             # 维护页（桌面）
    ├── hifi-mobile-maintain.html              # 维护页（移动）
    ├── hifi-desktop-maintain-processing.html  # 维护流程 · 处理中（桌面）
    ├── hifi-desktop-maintain-complete.html    # 维护流程 · 完成（桌面）
    ├── hifi-mobile-maintain-processing.html   # 维护流程 · 处理中（移动）
    ├── hifi-mobile-maintain-complete.html     # 维护流程 · 完成（移动）
    ├── design_system.md                       # 设计系统（样式与组件规范）
    └── design.md                              # 设计文档（流程与实现说明）
```

- 页面职责：
  - 查询页：精确匹配查询、空态与结果表展示、列换行策略与交互约束。
  - 维护页：四行表单结构与主按钮，流程状态包含处理中遮罩与完成弹框。
  - 顶部入口标签：查询页为“维护视频数据”，维护页为“返回查询”。

- 进程模型：
  - 当前阶段为静态预览与评审；不包含可运行业务代码。
  - 实现阶段：UI 框架待定；IO 通过 `services` 与现有模块执行；避免长期阻塞（必要时使用轻量线程/异步提示）。
- 数据与配置来源：
  - 默认数据库与路径约定沿用现有 CLI/模块；具体接入在生成阶段落地。

## 4. 数据流与关键交互（映射推荐工作流程）

1) 数据库初始化（安全确认）：
- 初始化/重置数据库（需要输入 “yes” 确认）；
- 自动创建路径/目录；
- 验证表结构正确（仅通过 `_create_tables()`，无迁移）。

2) 扫描目录→生成 CSV：
- 指定目录、标签（逗号分隔）、逻辑路径；
- 生成 CSV 到用户指定位置（推荐 `output/...`）；
- 显示概要（文件数、错误数、示例行）。

3) CSV 人工检查与校验：
- UI 内预览 CSV（分页/筛选）；
- 基本规则校验（空路径、不可读文件、异常字段）；
- 标注潜在问题（不自动修复）。

4) 合并 CSV → 数据库：
- 指定 CSV 文件与数据库；
- 执行合并，显示进度与统计（插入/更新/标记缺失/替换/重复）；
- 记录合并历史（`merge_history`）。

5) 查询视频（按 `video_code`）：
- 单个或多个 code（大小写不敏感）；
- 显示关键字段（code、文件大小、逻辑路径等）。

6) 统计分析：
- 基本统计、按标签/分辨率/时长分布、增强统计；
- 表格与图表展示。

7) 导出与简化导出：
- 导出 CSV/JSON；
- 简化导出（仅 filename_without_ext、filesize、logical_path）；
- 输出到指定文件或默认命名。

8) 诊断与调试：
- `scan_history` / `merge_history` 快速查看；
- DB 体检（表存在性、记录数、索引检查）；
- 常见问题提示与命令建议。

9) 设置与偏好：
- 默认数据库路径、默认标签与逻辑路径模板；
- FFmpeg 可用性检测与安装指引；
- Git hooks 安装与状态检查（调用 `./setup_hooks.sh`）。

## 5. 合规与安全

- 无迁移无兼容：
  - 严禁迁移脚本；任何结构变更只允许在 `_create_tables()`；
  - UI 提供“重置数据库”而非迁移。
- 文档与数据脱敏：
  - UI 示例与导出演示使用通用占位符（如 `TEST-001`）；
  - 不在版本控制文件中写入真实敏感数据（遵守 `DEVELOPMENT_GUIDELINES.md`）。
- 钩子与提交检查：
  - 提供安装钩子的入口与状态显示；
  - UI 文案清晰说明允许的“只读自检”范围。
- 本地安全：
  - 仅绑定 `localhost`；
  - 不开放远程访问；
  - 明确端口与访问控制说明。

## 6. TDD 小步迭代与测试计划

> 原则：每个 Step 一个测试文件；测试放在 `tests/ui/`；优先验证服务层与数据流，不进行脆弱的像素级 UI 测试。

- 测试命名约定：`tests/ui/test_step_XX_<short>.py`
- 使用 `pytest` 与 `tmp_path`、`monkeypatch`/`mock`；
- 尽量复用现有 `tests/tool_video_info_collector/test_videos/` 作为示例数据来源。

### Step 列表与验收标准

1) Step 01 启动与环境检测（`test_step_01_boot_and_env.py`）
- 能构造配置对象，检测 FFmpeg/SQLite 可用性并给出提示；
- 不启动真实 UI，仅验证服务层与配置加载。

2) Step 02 数据库初始化（`test_step_02_init_db.py`）
- 能在临时路径创建/重置数据库；
- 验证表结构存在：`video_info`、`video_tags`、`scan_history`、`video_master_list`、`merge_history`。

3) Step 03 扫描目录到 CSV（`test_step_03_scan_to_csv.py`）
- 模拟输入目录与参数，生成 CSV 文件；
- 验证 CSV 基本字段完整与行数合理。

4) Step 04 CSV 校验与预览（`test_step_04_csv_validate.py`）
- 能解析 CSV 并检测空值/非法路径；
- 返回校验报告数据结构（错误计数、示例行）。

5) Step 05 合并 CSV 到数据库（`test_step_05_merge_csv.py`）
- 触发合并，验证插入/更新/缺失标记的统计数；
- 验证 `merge_history` 记录增加。

6) Step 06 查询（`test_step_06_search_by_code.py`）
- 按多个 `video_code` 查询，返回期望字段集合；
- 大小写不敏感与空格/逗号分隔解析正确。

7) Step 07 统计（`test_step_07_stats_basic.py`）
- 基本统计与标签/分辨率/时长分组统计返回正确结构；
- 数值范围与字段名符合术语表。

8) Step 08 导出与简化导出（`test_step_08_export.py`）
- 导出 CSV/JSON 成功；
- 简化导出内容格式正确（`filename_without_ext filesize logical_path`）。

9) Step 09 状态管理（`test_step_09_state_management.py`）
- 在会话状态中保存/读取当前 DB 路径、标签、逻辑路径；
- 切换页面不丢失关键状态。

10) Step 10 错误处理与提示（`test_step_10_error_handling.py`）
- 模拟异常（无权限/损坏文件/不可读目录），能返回用户可读的错误信息；
- 不崩溃，记录诊断信息。

11) Step 11 设置与偏好（`test_step_11_settings.py`）
- 读写设置值到本地配置（不写入版本控制区）；
- 默认值符合文档约定（默认数据库路径等）。

12) Step 12 钩子安装与合规（`test_step_12_hooks_and_policy.py`）
- 调用脚本安装钩子时返回成功/失败状态；
- 展示无迁移政策摘要与只读自检范围说明的数据结构。

> 可选后续 Step：重复检测可视化、替换场景引导、批量操作确认、性能与大目录分页、导出筛选器、统计图丰富化。

## 7. 测试策略与覆盖面

- 层次：
  - 服务层单元测试（首选，稳定、可重复）；
  - 轻量集成测试（对数据库与文件 IO 做真实操作但控制规模）。
- 数据：
  - 仅使用脱敏/示例数据（遵守 `DEVELOPMENT_GUIDELINES.md`）；
  - 不对 `output/` 以外的真实用户数据操作。
- 构建：
  - 所有改动后运行 `pytest tests/ -v`；
  - 失败即修复，直至全部通过。

## 8. 依赖与安装

- 运行依赖：
  - `streamlit`（UI）
  - `ffmpeg`/`ffprobe`（元数据提取）
  - `sqlite3`（标准库）
- 安装指引：
  - macOS：`brew install ffmpeg`
  - Windows：下载 FFmpeg 二进制并配置 PATH；
- 后续将在 `pyproject.toml` 添加 `streamlit` 依赖（本设计阶段不改代码）。

## 9. 配置项与默认值

- 默认数据库：`output/video_info_collector/database/video_database.db`
- 默认扫描参数：扩展名集合、是否递归、标签与逻辑路径模板；
- 端口与绑定地址：默认随机端口、绑定 `localhost`；
- 所有用户偏好仅存本地，不提交到版本控制。

## 10. 术语与一致性

- 严格遵守 `TERMINOLOGY.md`：字段名、返回结构、统计项命名；
- UI 与服务层对齐已有术语（如 `video_code`、`file_status`、`merge_history`）。

## 11. 性能与稳定性

- 大目录扫描分页加载；
- IO 操作可中断/取消；
- 统计与导出对大数据量进行分批或流式写入。

## 12. 风险与缓解

- FFmpeg 缺失：提供检测与安装指引；
- 权限问题：明确错误与目录选择建议；
- 数据库损坏：指向“重置数据库”能力与备份建议；
- 术语不一致：引入术语校验与测试覆盖。

## 13. 路线图（里程碑）

- M1：服务层与 TDD 基础测试（Step 01–06）
- M2：统计与导出（Step 07–08）
- M3：状态与设置（Step 09–11）
- M4：合规与钩子（Step 12）
- M5：可选增强（图表、重复检测可视化、性能优化）

## 14. 运行示例（与 CLI 对齐）

- 初始化数据库：
```bash
python -m tools.video_info_collector --init-db --database projects/media_library.db
```
- 扫描到 CSV：
```bash
python -m tools.video_info_collector /media/movies --output temp_movies.csv --tags "电影" --path "媒体库/电影"
```
- 合并到数据库：
```bash
python -m tools.video_info_collector --merge temp_movies.csv --database projects/media_library.db
```
- 查询与统计（UI 内对应页面提供等价操作）。

## 15. 参考与规范

- `debug/video_info_collector/CLI_DEMO.md`（推荐工作流程）
- `DEVELOPMENT_GUIDELINES.md`（开发守则与安全）
- `NO_MIGRATION_POLICY.md`（无迁移无兼容政策）
- `tools/video_info_collector/README.md`（模块说明）

---

> 注：本设计文档为实现前提与评审依据，后续实现与测试需严格对齐本文档；任何偏离需在文档中先修改并获批准（遵守“设计文档至上原则”）。

---

## 附录：产品流程总览（简表）

- 01 数据库初始化：输入数据库路径、确认“yes”、结构验证、日志窗口。
- 02 扫描到 CSV：目录、标签、逻辑路径、递归/扩展名、进度与示例预览、输出位置。
- 03 CSV 校验与预览：选择 CSV、规则选择、校验报告、分页/筛选/搜索的预览表、导出校验报告。
- 04 合并到数据库：选择 CSV/DB、强制合并选项、进度条、合并统计（新增/更新/缺失/替换/重复）、合并历史与报告导航。
- 05 查询与统计：按 `video_code` 查询关键字段；统计类型选择（基本/标签/分辨率/时长/增强）并展示图表/表格。
- 06 导出与简化导出：选择数据库与格式（csv/json）、输出文件；简化导出为文本（`filename_without_ext filesize logical_path`）。
- 07 诊断与日志：快捷查询 `scan_history/merge_history/video_info`、体检（表/记录数/索引）、常见问题与命令建议、操作日志窗口。
- 08 设置与偏好：默认数据库路径、默认标签与逻辑路径模板、FFmpeg 检测、Git hooks 安装、保存设置。

## 附录：组件映射参考（Streamlit）

- 输入类：`st.text_input`、`st.text_area`、自定义文件/目录选择器。
- 控件类：`st.checkbox`、`st.selectbox`、`st.multiselect`、`st.button`。
- 展示类：`st.table`、`st.dataframe`、`st.metric`、`st.progress`、`st.chart`。
- 布局：`st.sidebar`（全局导航）、`st.tabs`（查询/统计分栏）、栅格布局（`columns`）。
- 状态：`st.session_state` 保存 DB 路径、标签、逻辑路径等。

## 与高保真与设计系统的对齐声明

- 查询约束与交互：仅支持精确匹配；禁用空查询与模糊查询；输入不符时禁用查询按钮并提示；支持回车触发；初始进入查询页自动聚焦搜索框；空态容器显示“请输入关键词进行查询”并隐藏结果表。
- 表格列换行策略：`视频`与`大小`列不换行（`white-space: nowrap`）；`路径`列允许换行并启用 `word-break: break-all`，保证小屏可读性；启用斑马线与行悬停。
- 维护页表单与状态：四行结构（目录输入+选择目录、标签输入、逻辑路径输入、开始维护），桌面 `.form-row { display:flex; gap:8px; align-items:center; margin:10px 0; }`；点击“开始维护”显示全屏遮罩（不可关闭、锁定滚动），完成后弹框“维护完成”（支持 `Esc` 关闭并返回查询，解除滚动锁定）。
- 移动端适配：设备框 375×667；使用单列布局，按钮置于输入下方；维护页可隐藏“逻辑路径”输入；弹框宽度与间距做最小化适配，保持与桌面一致的视觉基调（详见高保真页面）。

> 注：为精简文档与避免信息分散，原“原型草案”中的通用流程与组件映射信息已并入本设计文档的附录；不再保留单独草案文件。