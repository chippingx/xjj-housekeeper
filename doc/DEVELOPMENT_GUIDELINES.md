# 开发规范（长期遵守）

本文件是项目的长期开发约束，面向后续开发者与 AI IDE：优先保留“仍需遵守”的原则与流程，避免记录短期状态与过时实现细节。

## 文档入口

- 项目快速认知：[`HANDOVER.md`](./HANDOVER.md)
- 术语与命名：[`TERMINOLOGY.md`](./TERMINOLOGY.md)
- 无迁移无兼容政策：[`NO_MIGRATION_POLICY.md`](./NO_MIGRATION_POLICY.md)

## 核心原则

### 1) 安全优先

- 任何涉及文件/数据库写入的改动，必须默认不覆盖、不删除、可回滚或可重建。
- 禁止在仓库内写入真实敏感信息（域名、用户路径、真实编号、账号信息等）；示例必须使用占位符。

### 2) 最小影响

- 优先修改现有文件与现有结构，避免创建新的文件/目录/模块。
- 引入新依赖前，先确认仓库已使用该依赖；避免“为了方便”引入额外依赖。

### 3) 约定优先

- 代码风格、模块结构、命名规则优先遵循现有实现。
- 新增字段/参数/返回值命名必须符合术语表；发现不一致优先改代码，不要“改术语表适配代码”。

### 4) 变更必验证

- 任何代码改动完成后必须运行测试套件（至少 `pytest -q`）。
- 若变更影响打包或桌面端入口，需额外验证启动脚本与打包流程不被破坏。

## 无迁移无兼容政策（强制）

本项目遵循“无迁移无兼容”：不写迁移、不保兼容；需要结构变更时直接改创建逻辑并重建数据。

详情见：[`NO_MIGRATION_POLICY.md`](./NO_MIGRATION_POLICY.md)。

## 目录与职责（约定）

- `tools/`：可复用的工具模块（CLI/核心逻辑/存储等）。
- `ui/`：桌面 UI（当前为 Tkinter），与 `tools/` 通过服务层对接。
- `startup/`：启动与打包脚本（桌面端入口、构建 `.app` 等）。
- `config/`：应用元信息与跨模块配置（例如 `config/app_meta.json`）。
- `doc/`：开发规范与长期约束文档（本目录）。
- `tests/`：回归与单元测试套件。

## 配置管理（关键点）

### filename_formatter 配置

- 用户规则文件 `rename_rules.yaml` 处于 `.gitignore` 中，不应提交到仓库。
- 仓库提供示例：`tools/filename_formatter/rename_rules.yaml.example`。
- 工具默认读取 `RENAME_RULES_PATH` 指向的 YAML；未设置时会尝试默认路径 `tools/filename_formatter/rename_rules.yaml`。

### 应用版本与元信息（桌面端）

- Python 包版本：`pyproject.toml` 的 `[project].version`
- 桌面端展示/元信息：`config/app_meta.json`（例如 `version`、`release_date`、`app_name`）
- macOS `.app` 版本：由打包配置（PyInstaller spec）写入 `Info.plist` 的版本字段

## 文档与示例安全

### 脱敏规则

- 域名：使用 `example.com` / `example.net` / `demo.org`
- 编号：使用 `TEST-001` / `DEMO-002` / `SAMPLE-003`
- 路径：使用相对路径或通用占位路径（例如 `/path/to/videos`）

### 提交前自检（仅检查版本控制文件）

```bash
git ls-files '*.md' '*.py' | xargs grep -nE '\b([A-Za-z0-9-]+\.)+(com|net|org|xyz)\b' || true
git ls-files '*.md' '*.py' | xargs grep -nE '\b[A-Z]{2,6}-[0-9]{2,5}\b' || true
```

## 测试约定

```bash
pytest -q
python -m pytest tests/tool_filename_formatter/ -q
python -m pytest tests/tool_video_info_collector/ -q
python -m pytest tests/ui/ -q
```

## AI 开发准则（用于后续维护）

- 不写入或传播敏感信息；示例必须脱敏。
- 不随意创建文件；能改现有文件就不新建。
- 不随意引入新依赖；先确认仓库已有依赖再使用。
- 不添加无请求的代码注释；避免在核心逻辑中加入“解释性噪音”。
- 不引入迁移/兼容代码；需要变更结构就重建。
- 每次提交前（或交付前）确保测试通过，且不破坏启动/打包脚本。
