# 交接文档（xjj_housekeeper）

本文件面向对项目不熟悉的后续开发者或 AI IDE，旨在用最短时间建立对项目的清晰认知：设计思想、结构、规范、配置、运行与测试、当前状态与改进路线。

## 1. 项目概览

- 目标：为本地下载的视频文件提供整理工具集合。
  - 已实现：文件名规范化工具（filename_formatter）- **默认扁平化输出，安全重命名**
  - 规划中：视频文件清单收集工具、跨平台 GUI（Windows/macOS）
- 语言与版本：Python 3.10+
- 管理与依赖：Poetry；运行依赖 pyyaml、python-dotenv；开发依赖 pytest、pytest-cov、pytest-mock、pytest-xdist
- 系统依赖：FFmpeg (ffprobe)、SQLite3
- 当前版本：0.1.0（未打包发布）

## 2. 目录结构与职责

- README.md：项目级说明、快速开始、路线图
- pyproject.toml：依赖与构建配置（Poetry，package-mode=false）
- tools/
  - filename_formatter/
    - formatter.py：核心逻辑（配置加载、规则应用、格式化与批量重命名）
    - cli.py：命令行入口（ArgumentParser + main）
    - __main__.py：支持 `python -m tools.filename_formatter`
    - README.md：工具说明与配置优先级文档
    - rename_rules.yaml：默认规则与设置（扩展名、最小文件大小、替换规则）
- tests/
  - conftest.py：将项目根加入 sys.path，便于导入
  - tool_filename_formatter/
    - test_filename_formatter.py：核心逻辑单测
    - test_cli_filename_formatter.py：CLI 单测

## 3. 安装与运行

### 3.1 环境要求
- Python 3.10+
- 系统依赖：
  - **FFmpeg** (包含 ffprobe)：用于视频元数据提取
    - macOS: `brew install ffmpeg`
    - Ubuntu/Debian: `sudo apt-get install ffmpeg`
    - Windows: 下载并安装 FFmpeg 二进制文件
  - **SQLite3**: 通常系统自带，Python 内置支持

### 3.2 安装依赖
- 推荐：Poetry
  - `poetry install`
  - 开发环境：`poetry install --with dev,test`
- 或 venv + pip：
  - 运行依赖：`pip install pyyaml python-dotenv`
  - 开发依赖：`pip install pytest pytest-cov pytest-mock pytest-xdist`

### 3.3 运行工具
- 文件名规范化工具（递归处理子目录）：
  - `python -m tools.filename_formatter <目录路径>`
- 视频信息收集工具：
  - `python -m tools.video_info_collector scan <目录路径>`

## 4. 配置与优先级

- 配置文件：`tools/filename_formatter/rename_rules.yaml`
  - `settings.video_extensions`：默认 `[".mp4", ".mkv", ".mov"]`
  - `settings.min_file_size_bytes`：默认 `104857600`（100MB）
  - `rename_rules`：字符串替换规则（按顺序执行）
- 环境变量
  - `RENAME_RULES_PATH`：规则 YAML 路径（绝对或相对项目根）
  - `MIN_VIDEO_SIZE_BYTES`：覆盖最小文件大小（字节）
- 生效优先级（以 FilenameFormatter 为准）
  - 扩展名 video_extensions：构造参数 > YAML settings.video_extensions > 默认值；内部会统一为小写并补“.”
  - 最小大小 min_file_size：构造参数 > 环境变量 MIN_VIDEO_SIZE_BYTES > YAML settings.min_file_size_bytes > 默认 100MB
  - 规则文件路径：default_rules_path（若传入）> 环境变量 RENAME_RULES_PATH > 默认 `tools/filename_formatter/rename_rules.yaml`
- "项目根"推导：使用 `tools/path_utils.py` 中的 `ProjectPathManager`，提供多种稳定的推导策略：
  - 环境变量优先（`XJJ_HOUSEKEEPER_ROOT`）
  - 标志文件检测（`pyproject.toml`、`README.md` 等）
  - 向上查找项目根目录，避免硬编码相对路径层级
  - 支持不同部署环境（开发、打包、容器等）

## 5. 核心设计（tools/filename_formatter/formatter.py）

- 数据结构
  - `@dataclass RenameResult`
    - `original`: 原文件完整路径
    - `new`: 目标文件完整路径
    - `status`: `"success" | "skipped: same name" | "skipped: target exists" | "error: ..."`
- 关键方法
  - `format_filename(filename: str) -> str`
    - 规范化策略：将字母部分大写、与数字之间强制连字符，保留原扩展名
    - 匹配模式：优先大写 `^([A-Z]+)[-]*(\d+).*$`，否则小写回退。无法识别则返回原名
  - `apply_rename_rules(filename: str) -> str`
    - 按 `rename_rules` 顺序执行 `str.replace`，再调用 `format_filename`
  - `is_standard(filename: str) -> bool`
    - 当前实现：`^[A-Z]+-?\d+\.mp4$`（仅对 .mp4 校验为 True）
  - `rename_in_directory(base_path: str, include_subdirs: bool=False, flatten_output: bool=False, conflict_resolution: str="skip", dry_run: bool=False, log_operations: bool=False, verify_size: bool=False) -> List[RenameResult]`
    - **默认扁平化输出**：`flatten_output=True` 时将所有子目录文件移动到根目录
    - **冲突处理策略**：`conflict_resolution="skip"` 跳过同名文件，`"rename"` 自动添加序号
    - **安全保障**：绝不覆盖现有文件，确保数据安全
    - 仅处理配置的扩展名（大小写不敏感）
    - 跳过隐藏文件（以`.`开头）
    - 小于 `min_file_size` 的文件直接跳过（不记录结果）
    - `include_subdirs=True` 时递归扫描；返回 `RenameResult` 列表
    - **预览模式**：`dry_run=True` 时仅预览操作，不实际修改文件
    - **操作日志**：`log_operations=True` 时记录操作便于回滚
    - **文件验证**：`verify_size=True` 时进行轻量级文件大小验证

实现要点：
- 配置加载 `_load_config(...)` 会兼容旧结构，将 `settings` 中的字段展平使用
- 规则替换为简单字符串替换（非正则），允许多条顺序执行
- 安全重命名：永不覆盖已存在目标；同名直接记录为 `skipped: same name`

## 6. CLI 设计（tools/filename_formatter/cli.py）

- 用法：`python -m tools.filename_formatter <目录路径> [选项]`
- 可用参数：
  - `--dry-run` - 预览模式：显示将要执行的操作，但不实际修改文件
  - `--conflict-resolution {skip,rename}` - 同名文件冲突处理方式（默认：skip）
  - `--log-operations` - 记录所有操作到轻量级日志文件
  - `--verify-size` - 验证文件大小（轻量级验证）
  - `--version` - 显示版本信息
- 行为：
  - **默认扁平化输出**：所有子目录文件自动移动到根目录（`flatten_output=True`）
  - 总是递归处理（`include_subdirs=True`）
  - 构造 `FilenameFormatter(default_rules_path=None)`，鼓励通过环境变量选择规则文件
  - 输出处理目录、扩展名、最小大小、规则路径、扁平化状态
  - 打印每条结果行和统计（总计/成功/跳过/失败）
- 退出码：
  - 0：成功（无错误）
  - 1：执行失败或存在错误条目
  - 2：目录不存在或路径非目录
  - 130：用户中断

## 7. 测试与覆盖（pytest）

- 运行：`pytest -q`
- 覆盖点：
  - 格式化逻辑（大小写、连字符）
  - 规则应用与优先级（default_rules_path、环境变量覆盖）
  - `is_standard` 行为
  - 批量重命名：非递归/递归、目标已存在、同名、最小大小门槛
  - CLI：基本重命名、递归+规则、无效目录

### 7.1 回归测试策略

项目采用基于真实场景的回归测试策略，确保文件名清理功能的稳定性：

- **测试数据目录**：`tests/original_folder/`
  - 作用：保存各种典型的原始文件名模式，作为"黄金标准"测试数据
  - 原则：**此目录下的文件不得修改**，保持原始状态以便重复测试
  - 内容：包含真实场景中常见的文件名模式（网站前缀、后缀、目录结构等）

- **测试用例覆盖**：
  - 标准格式文件：`TST-005/TST-005.mp4`
  - 需要清理后缀：`TST-004ch/TST-004ch.mp4`
  - 复杂前后缀：`TST-006_CH.HD/TST-006_CH-nyap2p.com.mp4`
  - 网站前缀：`btnets.net_TST-002.mp4`
  - 根目录文件：`TST-001.mp4`

- **测试流程**：
  1. 每次测试前拷贝 `original_folder` 到临时目录
  2. 在拷贝目录上运行文件名清理工具
  3. 验证清理结果是否符合预期
  4. 清理临时文件，保持原始数据不变

- **文件格式**：测试文件使用最小化的假mp4文件（减少存储空间），但保持有效的mp4格式以通过工具的文件类型检查

## 8. 路径管理方案（tools/path_utils.py）

### 8.1 问题背景
原有的路径推导方式 `Path(__file__).resolve().parents[2]` 在某些部署环境中不够稳定：
- 代码被打包时，文件结构可能发生变化
- 在容器环境中运行时，相对路径可能不准确
- 不同的运行方式（直接运行、模块导入等）可能导致路径错误

### 8.2 新的解决方案
`ProjectPathManager` 类提供多种稳定的项目根目录推导策略：

#### 推导策略（按优先级）
1. **环境变量优先**：`XJJ_HOUSEKEEPER_ROOT`
   - 允许用户显式指定项目根目录
   - 适用于容器化部署和CI/CD环境

2. **标志文件检测**：向上查找包含以下文件/目录的路径
   - `pyproject.toml`（Python项目配置）
   - `README.md`（项目说明）
   - `HANDOVER.md`（交接文档）
   - `.git`（Git仓库）
   - `tools`（工具目录）

3. **相对路径回退**：支持传入相对路径作为回退方案

4. **当前工作目录**：从当前工作目录开始向上查找

5. **脚本目录**：从 `sys.path[0]` 开始查找

#### 主要API
```python
from tools.path_utils import ProjectPathManager, get_project_root, get_config_path

# 获取项目根目录
project_root = get_project_root(calling_file=__file__)

# 获取配置文件路径
config_path = get_config_path("tools/filename_formatter/rename_rules.yaml", calling_file=__file__)

# 解析路径（绝对路径直接返回，相对路径基于项目根解析）
resolved_path = ProjectPathManager.resolve_path("some/relative/path", calling_file=__file__)
```

#### 环境变量配置
```bash
# 设置项目根目录（可选）
export XJJ_HOUSEKEEPER_ROOT=/path/to/project

# 或在 .env 文件中设置
echo "XJJ_HOUSEKEEPER_ROOT=/path/to/project" >> .env
```

### 8.3 迁移说明
- 所有工具模块已更新使用新的路径管理方案
- 向后兼容：如果环境变量未设置，会自动使用标志文件检测
- 缓存机制：项目根目录会被缓存，避免重复计算
- 错误处理：无法确定项目根目录时会抛出详细的错误信息

## 9. 示例

- 设置最小大小为 1 字节（便于测试）：
  - macOS/Linux: `export MIN_VIDEO_SIZE_BYTES=1`
  - Windows (PowerShell): `$env:MIN_VIDEO_SIZE_BYTES="1"`
- 指定规则文件：
  - macOS/Linux: `export RENAME_RULES_PATH=/abs/path/to/rename_rules.yaml`
- 运行：
  - `python -m tools.filename_formatter ~/Downloads/videos`

示例输出（节选）：
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
would skip: target exists: /path/to/videos/sub/ABC123.mp4 -> /path/to/videos/ABC-123.mp4

统计:
- 总计: 4
- 成功: 2
- 跳过(目标已存在): 1
- 跳过(同名): 1
- 失败: 0
```

## 9. 已知限制与改进建议

### 已实现功能
- ✅ **扁平化输出**：默认启用，简化文件结构
- ✅ **冲突处理**：支持跳过或自动重命名策略
- ✅ **预览模式**：`--dry-run` 安全查看操作
- ✅ **操作日志**：`--log-operations` 支持回滚
- ✅ **文件验证**：`--verify-size` 轻量级验证
- ✅ **安全保障**：绝不覆盖现有文件

### 待改进项目
- 规则能力受限：当前仅支持 `str.replace`；建议引入正则、规则分组、顺序/条件控制、启停开关
- `is_standard` 仅检查 `.mp4`：建议根据 `video_extensions` 动态生成校验模式，或仅校验主名部分
- 统计与可观测性有限：隐藏文件、非目标扩展、小文件跳过未计入统计；建议增加 `--verbose/--json` 以及详细原因统计
- 规则路径显示：CLI 输出的"使用规则文件"是固定字符串，可能与实际生效路径不一致；建议打印解析后的真实路径
- "项目根"推导脆弱：建议使用运行时 CWD、显式 CLI 参数 `--rules`，或通过 pyproject 配置
- 性能与并发：大规模文件处理可考虑多进程/线程；注意目标冲突、原子重命名与日志整合
- 日志体系：由 `print` 改为 `logging`，支持级别和 JSON 输出，便于集成
- 扁平化可选性：考虑添加 `--no-flatten` 参数保持目录结构的选择
- 回滚与安全：可新增 dry-run、变更日志与“撤销重命名”功能

## 10. 设计原则

- 配置优先，代码少侵入：YAML + 环境变量控制行为
- 安全重命名：不覆盖目标、无法识别格式原样保留
- 简洁可测：核心逻辑可单元测试，已有较全面 pytest 覆盖
- 可扩展：规则系统、校验模式、CLI 选项均保留扩展空间

## 11. 开发指南

- 开发环境
  - 推荐 Poetry：`poetry install`
  - 或手动安装：`pyyaml`、`python-dotenv`、`pytest`
- 代码风格
  - 建议引入 ruff/black/mypy 与 CI（尚未配置）
  - 保持已有类型注解风格与中英文输出一致性
- 提交流程
  - 修改核心逻辑需同步更新/新增测试，确保 `pytest -q` 全绿
  - 建议后续添加 GitHub Actions：pytest、lint、type-check

## 12. 扩展路线（建议）

- 短期
  - 规则系统正则化与分组
  - `is_standard` 与扩展名一致性改造
  - CLI 选项：`--no-recursive`/`--min-size`/`--exts`/`--rules`/`--dry-run`/`--verbose`/`--json`
  - 打印真实规则文件路径；详细统计与原因分布
- 中期
  - 新增“视频文件清单收集”工具（扫描目录导出 CSV/JSON：名称、大小、扩展名、时间戳等）
  - 简易 GUI（PySide6/Tkinter 或 Web 前端 + 本地服务）
  - 打包分发（pip 包、命令入口点）

## 13. API 速览

- Python
  - `from tools.filename_formatter import FilenameFormatter`
  - `fmt = FilenameFormatter(video_extensions=None, min_file_size=None, default_rules_path=None)`
  - `fmt.apply_rename_rules("kfa55.com@ABC123ch.mp4")  # -> "ABC-123.mp4"`
  - `fmt.rename_in_directory("/path", include_subdirs=True)  # -> List[RenameResult]`
- CLI
  - `python -m tools.filename_formatter /path/to/videos`
  - 环境变量：`RENAME_RULES_PATH`、`MIN_VIDEO_SIZE_BYTES`

## 14. 当前工作状态（2024年最新）

### 14.1 最近完成的工作

#### 依赖管理维护（已完成 ✅）
- **依赖分析完成**：全面分析了项目中使用的所有Python包和系统依赖
  - Python标准库：`json`、`os`、`subprocess`、`tempfile`、`datetime`、`pathlib`、`shutil`、`csv`、`sqlite3`、`argparse`
  - 第三方Python包：`pytest`、`pyyaml`、`python-dotenv`、`pytest-cov`、`pytest-mock`、`pytest-xdist`
  - 系统依赖：`FFmpeg (ffprobe)`、`SQLite3`

- **pyproject.toml更新完成**：
  - 添加了项目元数据（readme、requires-python、keywords、classifiers）
  - 补充了测试依赖：`pytest-cov`、`pytest-mock`、`pytest-xdist`
  - 添加了系统依赖说明注释

- **文档同步更新完成**：
  - `HANDOVER.md`：更新了安装说明、依赖列表、系统依赖安装方式
  - `README.md`：补充了系统依赖安装指南、测试命令、工具功能说明
  - `DEVELOPMENT_OUTLINE.md`：创建了完整的开发纲要文档

#### 回归测试验证（已完成 ✅）
- **测试目录结构调整**：将测试数据迁移到 `tests/tool_filename_formatter/test_data/` 新位置
- **集成测试更新**：更新了所有集成测试中的路径配置，确保测试在新位置正常运行
- **功能验证通过**：所有4个集成测试均成功通过，确认文件处理功能正常

### 14.2 当前项目状态

#### 工具功能状态
- **filename_formatter工具**：✅ 功能完整，测试通过
  - 核心功能：文件名规范化、批量重命名、安全重命名（不覆盖）
  - 默认行为：扁平化输出、递归处理子目录
  - 配置系统：YAML配置文件 + 环境变量覆盖
  - 测试覆盖：单元测试 + 集成测试 + 回归测试

- **video_info_collector工具**：✅ 功能完整，依赖已确认
  - 核心功能：视频元数据提取、CSV/JSON导出、SQLite存储
  - 系统依赖：FFmpeg (ffprobe) - 通过subprocess调用
  - 测试覆盖：完整的单元测试套件

#### 依赖管理状态
- **Python依赖**：✅ 已完整记录和配置
- **系统依赖**：✅ 已确认并在文档中说明安装方式
- **开发环境**：✅ Poetry配置完整，支持开发和测试依赖分离

### 14.3 后续待办事项

#### 高优先级
- [ ] **CI/CD流水线建设**
  - 配置GitHub Actions进行自动化测试
  - 添加代码质量检查（ruff/black/mypy）
  - 设置自动化依赖更新检查

- [ ] **代码质量提升**
  - 引入类型检查（mypy）
  - 统一代码格式化（black/ruff）
  - 添加pre-commit hooks

#### 中优先级
- [ ] **功能增强**
  - 规则系统正则化改造（当前仅支持字符串替换）
  - `is_standard`方法扩展支持所有视频格式
  - CLI选项增强：`--no-flatten`、`--verbose`、`--json`输出

- [ ] **可观测性改进**
  - 将print输出改为logging系统
  - 增加详细的操作统计和原因分布
  - 支持JSON格式的结构化输出

#### 低优先级
- [ ] **新工具开发**
  - 视频文件清单收集工具的GUI界面
  - 跨平台打包和分发
  - Web界面支持

### 14.4 开发环境说明

#### 当前配置
- Python版本：3.10+
- 包管理：Poetry
- 测试框架：pytest + 插件
- 项目结构：工具模块化，测试完整覆盖

#### 开发工作流
1. 使用Poetry管理依赖：`poetry install --with dev,test`
2. 运行测试：`pytest -q` 或 `poetry run pytest`
3. 代码修改后必须通过所有测试
4. 重要功能变更需要更新相关文档

#### 注意事项
- 所有配置文件路径使用相对于项目根目录的路径
- 测试数据保持在专门的测试目录中，不要修改原始测试数据
- 新功能开发需要同步添加测试用例
- 文档更新是代码变更的必要组成部分
- Poetry配置：当前使用混合配置格式（`[tool.poetry.dependencies]` + `[project.dependencies]`），会有警告但不影响功能
- 依赖更新后需要运行 `poetry lock` 更新锁定文件

## 15. 交接检查清单（给后续开发者/AI IDE）

### 基础环境检查
- [ ] 能运行 `pytest -q` 并通过
- [ ] 能运行 `poetry install` 成功安装依赖
- [ ] 系统已安装FFmpeg和SQLite3
- [ ] 理解配置优先级（构造参数/环境变量/YAML/默认）

### 功能理解检查
- [ ] 确认规则路径实际生效值，并在 CLI 输出中可见
- [ ] 明确跳过策略（隐藏文件、非扩展名、小文件）与统计口径
- [ ] 理解扁平化输出的默认行为和安全重命名机制
- [ ] 熟悉测试数据结构和回归测试流程

### 开发规范检查
- [ ] 阅读并理解 `DEVELOPMENT_GUIDELINES.md` 中的开发规范
- [ ] 了解依赖管理策略和配置文件管理原则
- [ ] 掌握测试开发规范和代码质量要求
- [ ] 对新增功能补充测试与文档

### 后续工作规划
- [ ] 规划并落地 CI、lint、type-check
- [ ] 评估规则系统正则化与 is_standard 改造
- [ ] 考虑可观测性和日志系统改进
- [ ] 制定新工具开发和GUI界面计划

---

项目元信息
- 名称：xjj-housekeeper
- 版本：0.1.0
- 运行依赖：python-dotenv、pyyaml
- 开发依赖：pytest、pytest-cov、pytest-mock、pytest-xdist
- 系统依赖：FFmpeg (ffprobe)、SQLite3
- 构建：Poetry（poetry-core）
- 最后更新：2024年（依赖维护和回归测试完成）