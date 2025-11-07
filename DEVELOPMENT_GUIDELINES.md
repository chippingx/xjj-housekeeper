# 开发规范与经验教训

## 📋 目录
- [核心开发原则](#核心开发原则)
- [无迁移无兼容政策](#无迁移无兼容政策)
- [文档安全性规范](#文档安全性规范)
- [术语表规范](#术语表规范)
- [目录结构规范](#目录结构规范)
- [数据脱敏规范](#数据脱敏规范)
- [配置管理规范](#配置管理规范)
- [测试开发规范](#测试开发规范)
- [代码风格规范](#代码风格规范)
- [经验教训总结](#经验教训总结)
- [反面教材与改进](#反面教材与改进)

---

## 🚨 无迁移无兼容政策

**核心原则**: 本项目严格遵循"无迁移无兼容"原则，详见 [`NO_MIGRATION_POLICY.md`](./NO_MIGRATION_POLICY.md)

### 关键要求
- ❌ **禁止** 任何数据库迁移代码
- ❌ **禁止** 向后兼容性代码  
- ❌ **禁止** `ALTER TABLE`、`_migrate_*` 等迁移相关代码
- ✅ **直接修改** `_create_tables()` 中的表结构
- ✅ **重新创建** 数据库而非迁移

**违规处理**: 发现迁移代码立即删除，无需保留任何历史兼容性。

---

## 🔒 文档安全性规范

### 1. 敏感信息保护原则 ⚠️ **安全强制要求**
**规则**: 所有文档、代码注释、示例和配置文件中严禁直接包含敏感信息，必须使用通用占位符。

### 2. 脱敏占位符规范
**标准占位符格式**:
- 域名: 使用 `example.com`、`test.net`、`demo.org` 等通用示例域名
- 编号: 使用 `TEST-001`、`DEMO-002`、`SAMPLE-003` 等通用编号
- 文件路径: 使用相对路径或通用示例路径

**示例对比**:
```markdown
❌ 错误: 输入文件 realsite.com_ABC-123.mp4
✅ 正确: 输入文件 example.com_TEST-001.mp4
```

### 3. 文档安全检查

#### 基于版本控制的安全检查策略 ⚠️ **重要原则**
**规则**: 只对纳入版本控制的文件进行敏感信息检查，`.gitignore` 中排除的文件无需检查。

**检查范围说明**:
- **需要检查**: 所有会提交到代码仓库的文件
- **无需检查**: `.gitignore` 中排除的文件和目录
  - `output/` - 程序输出文件
  - `__pycache__/` - Python缓存文件
  - `.operation_log_*` - 操作日志文件
  - `.backup_*` - 备份文件
  - `rename_rules.yaml` - 用户配置文件

**提交前必须检查**:
```bash
# 使用git ls-files确保只检查版本控制中的文件
# 检查文档中可能的敏感信息
git ls-files '*.md' | xargs grep -l "\.net\|\.com\|\.xyz" 2>/dev/null || true

# 检查代码注释中可能的敏感信息  
git ls-files '*.py' | xargs grep -l "\.net\|\.com\|\.xyz" 2>/dev/null || true

# 或者使用排除方式（推荐用于CI/CD）
grep -r "\.net\|\.com\|\.xyz" --include="*.md" --include="*.py" \
  --exclude-dir=output --exclude-dir=__pycache__ \
  --exclude="*.log" --exclude=".backup_*" .
```

**安全审查要求**:
- 所有**纳入版本控制**的文档更新必须进行敏感信息扫描
- 发现敏感信息必须立即脱敏处理
- 定期审查历史提交中的敏感信息泄露
- **程序输出文件**（如 `output/` 目录）可以包含真实数据，因为不会提交到仓库

---

## 🎯 核心开发原则

### 1. 设计文档至上原则 ⚠️ **最高优先级**
**规则**: 设计文档是需求和最终纲领，代码必须严格按照设计文档实现，绝对不允许为了适应代码而修改设计文档。

**核心要点**:
- 设计文档 = 需求规范 = 开发目标
- 代码必须符合设计文档，而不是相反
- 除非用户明确要求或认可，否则禁止修改设计文档
- 如果代码与设计文档不符，必须修改代码而非文档

**正确做法**:
```
❌ 严重错误: 发现代码实现与设计文档不符时，修改设计文档来适应代码
✅ 正确做法: 发现不符时，修改代码来符合设计文档要求
✅ 正确做法: 如需修改设计文档，必须先征得用户同意
```

### 2. 确认优先原则
**规则**: 当遇到不确定的需求或配置问题时，必须先与用户确认，不得擅自做决定。

**适用场景**:
- 配置文件路径不明确时
- 需要创建新文件或目录时
- 功能需求存在歧义时
- 测试行为需要调整时

**正确做法**:
```
❌ 错误: 为了通过测试，直接创建 config/rename_rules.yaml
✅ 正确: 发现配置路径问题时，停下来询问用户正确的配置方式
```

### 3. 最小影响原则
**规则**: 优先使用现有的文件和配置，避免创建不必要的新文件。

**实施要点**:
- 优先编辑现有文件而非创建新文件
- 使用项目既定的配置路径和结构
- 避免引入额外的复杂性

### 4. 强制性测试验证原则 ⚠️ **关键质量保证**
**规则**: 每次代码修改后必须运行完整测试套件，确保所有测试通过后才能认为任务完成。

**核心要点**:
- 代码修改 = 必须测试验证 = 质量保证
- 测试失败 = 任务未完成 = 需要继续修复
- 不允许以"大部分测试通过"为理由忽略失败的测试
- 环境问题导致的测试失败需要明确区分和记录

**强制执行流程**:
```bash
# 1. 每次代码修改后立即运行完整测试
pytest tests/ -v

# 2. 检查测试结果，必须全部通过（除明确的环境问题外）
# ✅ 正确状态: 322 passed, 2 skipped
# ❌ 错误状态: 320 passed, 2 failed, 1 error

# 3. 如有失败，必须修复后重新测试
# 4. 只有测试全部通过才能标记任务完成
```

**错误案例反思**:
```
❌ 严重错误: 发现测试失败但认为"大部分通过就够了"
❌ 严重错误: 没有运行测试就认为代码修改完成
❌ 严重错误: 测试失败后修改测试而不是修改代码
✅ 正确做法: 测试失败时分析原因，修复代码直到测试通过
✅ 正确做法: 区分代码问题和环境问题，记录环境问题
```

### 5. 术语表一致性原则 ⚠️ **命名规范强制执行**
**规则**: 所有开发必须严格遵守项目术语表([TERMINOLOGY.md](TERMINOLOGY.md))，确保字段命名、变量命名、API接口的一致性。

**核心要点**:
- 术语表 = 命名标准 = 强制规范
- 所有新增代码必须符合术语表规范
- 发现不一致时必须修改代码而非术语表
- 术语表更新需要系统性地更新所有相关代码

**强制检查项目**:
- **数据库字段**: 使用`video_code`而非`code`或`search_code`
- **API方法**: 使用`search_videos_by_video_codes()`而非`search_videos_by_codes()`
- **CLI参数**: 使用`--search-video-code`而非`--search-code`
- **变量命名**: 使用`file_status`而非`status`

**违规检测命令**:
```bash
# 检测非标准video_code使用
grep -r "search_code\|vid_code" --include="*.py" .

# 检测非标准方法名
grep -r "search.*by.*codes[^)]" --include="*.py" .

# 检测CLI参数不一致
grep -r "search-code[^s]" --include="*.py" .
```

**正确做法**:
```
❌ 错误: 为了快速实现功能使用简化的命名
❌ 错误: 不同地方使用不同的字段名称
❌ 错误: 修改术语表来适应现有代码
✅ 正确: 严格按照术语表进行命名
✅ 正确: 发现不一致时修改代码符合术语表
✅ 正确: 新增术语时先更新术语表再实现代码
```

---

## 📚 术语表规范

### 1. 术语表强制执行
**规则**: 项目术语表([TERMINOLOGY.md](TERMINOLOGY.md))是所有命名的最高标准，任何代码、文档、测试都必须严格遵守。

**术语表覆盖范围**:
- **数据库字段命名**: 所有表结构和字段名称
- **Python变量命名**: 类属性、函数参数、局部变量
- **API接口命名**: 方法名、返回值字段名
- **CLI参数命名**: 命令行参数和选项
- **文件命名规范**: 模块文件、测试文件命名

---

## 📁 目录结构规范

### 1. 启动相关文件统一管理 ⚠️ **强制要求**
**规则**: 所有启动相关的脚本、程序、文档必须统一存放在`startup/`目录下管理。

**startup目录内容规范**:
- **桌面应用**: `xjj_housekeeper_desktop_streamlit.py` - Streamlit+PyWebView桌面程序
- **构建脚本**: `build_streamlit_desktop.py` - 桌面应用打包脚本
- **启动脚本**: 
  - `run-streamlit-desktop.sh/bat` - PyWebView桌面版本启动
  - `start-desktop.sh/bat` - 浏览器版本启动
- **相关文档**: `README_DESKTOP.md` - 桌面应用专门文档

**路径引用规范**:
```bash
# ✅ 正确：startup目录中的脚本必须能找到项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# ✅ 正确：Python程序中引用项目根目录
project_root = Path(__file__).resolve().parent.parent

# ❌ 错误：硬编码相对路径
cd ../ui  # 可能导致路径错误
```

**禁止事项**:
- ❌ 在项目根目录直接放置启动脚本
- ❌ 启动相关文件散落在项目各处
- ❌ 不规范的路径引用

**强制检查项目**:
```bash
# 检查项目根目录是否有启动脚本
ls -la *.sh *.bat | grep -v "startup/" && echo "发现违规启动文件"

# 检查startup目录结构
ls -la startup/ | grep -E "(xjj_housekeeper|build_.*desktop|run.*desktop|start.*desktop)"
```

### 2. 术语一致性检查
**规则**: 开发过程中必须定期进行术语一致性检查，确保没有违规使用。

**检查方法**:
```bash
# 自动检查脚本
./scripts/check_terminology.sh

# 手动检查命令
grep -r "search_code\|vid_code" --include="*.py" .
grep -r "search.*by.*codes[^)]" --include="*.py" .
grep -r "search-code[^s]" --include="*.py" .
```

**违规处理**:
- 发现违规立即修复
- 不允许修改术语表来适应代码
- 系统性检查相关代码确保完整修复

### 3. 术语表维护流程
**规则**: 术语表的任何修改都需要经过严格的评估和系统性更新。

**维护步骤**:
1. **评估影响**: 分析术语修改的影响范围
2. **更新术语表**: 在TERMINOLOGY.md中更新定义
3. **系统性修改**: 更新所有相关代码、测试、文档
4. **验证完整性**: 运行完整测试套件确保功能正常
5. **更新检查脚本**: 修改自动检查规则

---

## 📁 目录结构规范

### 1. 项目目录组织
**规则**: 保持清晰的目录结构，便于代码维护和理解。

---

## 🔒 数据脱敏规范

### 1. 脱敏原则与目标
**规则**: 项目中**纳入版本控制**的敏感数据必须进行脱敏处理，确保代码可以安全地用于演示、分享和开源。

#### 基于版本控制的脱敏策略 ⚠️ **重要区分**
**脱敏范围**:
- **必须脱敏**: 所有会提交到代码仓库的文件
  - 源代码文件 (`.py`, `.yaml`, `.md` 等)
  - 测试数据和示例文件
  - 配置模板文件
- **无需脱敏**: `.gitignore` 中排除的文件
  - `output/` - 程序输出可以包含真实数据
  - 用户的个人配置文件 (`rename_rules.yaml`)
  - 临时文件和日志文件

**脱敏目标**:
- 移除**版本控制文件**中的真实域名和网站标识
- 替换**代码和文档**中的敏感编号和标识符
- 清理**测试数据**中的个人信息
- 确保**示例数据**的通用性和安全性

### 2. 脱敏实施策略

#### 系统性脱敏流程
1. **范围确定**: 使用 `git ls-files` 确定需要脱敏的文件范围
2. **分类处理**: 区分代码文件、测试文件、配置文件、文档文件
3. **批量替换**: 使用一致的替换规则进行批量处理
4. **验证测试**: 确保脱敏后功能正常
5. **文档更新**: 同步更新相关文档

#### 脱敏替换规则
```yaml
# 域名脱敏规则（仅适用于版本控制文件）
真实域名 -> 通用示例域名
realsite.net -> example.net
actualsite.com -> test.com
livesite.xyz -> demo.xyz

# 编号脱敏规则（仅适用于版本控制文件）
敏感编号 -> 通用测试编号
ABC-123 -> TEST-001
DEF-456 -> DEMO-002
GHI-789 -> SAMPLE-003
```

### 3. 脱敏工具和方法

#### 基于版本控制的扫描
```bash
# 只扫描版本控制中的文件
git ls-files | grep -E "\.(py|yaml|md)$" | xargs grep -l "\.net\|\.com\|\.xyz" 2>/dev/null || true

# 扫描可能的敏感编号（仅版本控制文件）
git ls-files | xargs grep -l "[A-Z]{3,6}-[0-9]{3,4}" 2>/dev/null || true

# 传统方式（排除.gitignore中的目录）
grep -r "\.net\|\.com\|\.xyz" --include="*.py" --include="*.yaml" --include="*.md" \
  --exclude-dir=output --exclude-dir=__pycache__ \
  --exclude="*.log" --exclude=".backup_*" .
```

#### 批量替换工具（仅针对版本控制文件）
```bash
# 基于git ls-files的安全替换
git ls-files '*.py' | xargs sed -i 's/realsite\.net/example.net/g'
git ls-files '*.yaml' '*.md' | xargs sed -i 's/realsite\.net/example.net/g'

# 传统方式（排除.gitignore中的目录）
find . -type f -name "*.py" \
  -not -path "./output/*" \
  -not -path "./__pycache__/*" \
  -exec sed -i 's/realsite\.net/example.net/g' {} +

# ❌ 避免：对输出文件进行替换
# rename 's/realsite\.net/example.net/' output/*.mp4  # 不要这样做
```

### 4. 脱敏验证流程

#### 完整性验证（仅检查版本控制文件）
```bash
# 1. 扫描版本控制文件中的残留敏感数据
git ls-files | xargs grep -l "\.net\|\.com\|\.xyz" 2>/dev/null || echo "未发现敏感数据"

# 2. 运行完整测试套件
pytest tests/ -v

# 3. 验证功能正常
python -m tools.filename_formatter --help
```

#### 测试数据验证
- 确保测试用例使用通用数据
- 验证示例输出不包含敏感信息
- 检查文档中的示例代码

### 5. 脱敏维护策略

#### 持续监控
- 新增代码时检查敏感数据
- 定期进行全项目扫描
- 建立检查清单

#### 团队协作
- 代码审查时关注脱敏要求
- 提供脱敏工具和脚本
- 培训团队成员脱敏意识

### 6. 脱敏检查清单

#### 开发阶段检查（仅针对版本控制文件）
- [ ] 新增的**测试数据**是否使用通用示例？
- [ ] **配置模板文件**中是否包含敏感信息？
- [ ] **示例代码**是否使用了真实数据？
- [ ] **文档中的截图**是否包含敏感内容？
- [ ] 是否正确区分了版本控制文件和输出文件？

#### 发布前检查
- [ ] 是否对**版本控制文件**进行了敏感数据扫描？
- [ ] 所有测试用例是否通过？
- [ ] **文档示例**是否已经脱敏？
- [ ] **配置模板**是否使用示例数据？
- [ ] `.gitignore` 是否正确排除了包含真实数据的文件？

#### 脱敏完成验证
- [ ] 使用 `git ls-files` 扫描版本控制文件无残留敏感数据
- [ ] 所有测试用例正常通过
- [ ] 功能演示使用通用数据
- [ ] 文档和注释已同步更新
- [ ] 确认 `output/` 等输出目录已加入 `.gitignore`

### 7. 脱敏最佳实践

#### 预防性措施
```python
# ✅ 在代码中使用配置化的测试数据
TEST_DOMAINS = ["example.net", "test.com", "demo.xyz"]
TEST_VIDEO_IDS = ["TEST-001", "DEMO-002", "SAMPLE-003"]

# ❌ 避免在代码中硬编码真实数据
REAL_DOMAIN = "realsite.com"  # 不要这样做
```

#### 文档脱敏
```markdown
# ✅ 使用通用示例
输入文件: example.net_TEST-001.mp4
输出文件: TEST-001.mp4

# ❌ 避免真实示例
输入文件: realsite.com_ABC-123.mp4  # 不要这样做
```

#### 配置文件脱敏
```yaml
# ✅ 使用示例配置
rename_rules:
  - pattern: "example.net_"
    replace: ""
  - pattern: "test.com@"
    replace: ""

# ❌ 避免真实配置
rename_rules:
  - pattern: "realsite.com_"  # 不要这样做
    replace: ""
```

---

## 📦 依赖管理规范

### 1. 依赖分类与管理策略
**规则**: 严格区分运行依赖、开发依赖和系统依赖，确保项目的可移植性和可维护性。

#### 依赖分类标准
```toml
# pyproject.toml 依赖分类示例
[project]
dependencies = [
    "python-dotenv",  # 环境变量管理
    "pyyaml",        # YAML配置文件解析
]

[project.optional-dependencies]
dev = [
    "pytest",        # 测试框架
    "pytest-cov",    # 测试覆盖率
    "pytest-mock",   # 测试模拟
    "pytest-xdist",  # 并行测试
]
```

#### 系统依赖管理
**规则**: 系统依赖必须在文档中明确说明安装方式，不能假设用户环境已安装。

**正确做法**:
```markdown
### 系统依赖
- **FFmpeg** (包含 ffprobe)：用于视频元数据提取
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: 下载并安装 FFmpeg 二进制文件
- **SQLite3**: 通常系统自带，Python 内置支持
```

### 2. 依赖分析与维护流程

#### 定期依赖审查
**规则**: 每次添加新功能后，必须审查和更新依赖配置。

**审查步骤**:
1. **代码扫描**: 使用工具扫描所有import语句
2. **分类整理**: 区分标准库、第三方库、系统依赖
3. **配置更新**: 更新pyproject.toml和文档
4. **测试验证**: 确保依赖配置正确

**工具使用示例**:
```bash
# 扫描Python导入
grep -r "^import\|^from.*import" --include="*.py" .

# 检查第三方库使用
grep -r "import \(pytest\|yaml\|dotenv\)" --include="*.py" .
```

### 3. 依赖版本管理

#### 版本固定策略
**规则**: 生产依赖使用兼容性版本范围，开发依赖可以更宽松。

```toml
# ✅ 正确的版本管理
dependencies = [
    "python-dotenv>=0.19.0,<2.0.0",  # 兼容性范围
    "pyyaml>=6.0,<7.0",               # 主版本锁定
]

# ❌ 避免的做法
dependencies = [
    "python-dotenv",     # 无版本约束，可能导致兼容性问题
    "pyyaml==6.0.1",     # 过度严格，阻碍安全更新
]
```

### 4. 依赖冲突解决

#### 冲突检测与解决
**规则**: 使用Poetry的依赖解析能力，避免手动管理复杂依赖关系。

**最佳实践**:
```bash
# 检查依赖冲突
poetry check

# 查看依赖树
poetry show --tree

# 更新依赖
poetry update

# 锁定依赖版本
poetry lock
```

---

## ⚙️ 配置管理规范

### 1. 配置文件层次结构
```
项目根目录/
├── .env                    # 环境变量配置
├── tools/
│   └── filename_formatter/
│       └── rename_rules.yaml  # 工具专用配置 ✅ 正确位置
└── config/                 # ❌ 避免创建额外配置目录
```

### 2. 环境变量管理
**规范**: 所有配置路径必须使用相对于项目根目录的路径

**示例**:
```bash
# ✅ 正确
RENAME_RULES_PATH=tools/filename_formatter/rename_rules.yaml

# ❌ 错误
RENAME_RULES_PATH=config/rename_rules.yaml  # 不存在的路径
```

### 3. 配置文件同步
**规则**: 避免在多个位置维护相同的配置文件

**问题案例**:
- 同时存在 `tools/filename_formatter/rename_rules.yaml` 和 `config/rename_rules.yaml`
- 导致配置不一致和维护困难

---

## 📁 目录结构规范

### 1. 核心原则
**规则**: 实现目录必须保持纯净，只包含核心功能代码，严禁混杂debug代码和测试代码。

**目录职责划分**:
- **`tools/`**: 纯粹的功能实现代码
- **`tests/`**: 所有测试代码
- **`debug/`**: 调试和验证脚本
- **`output/`**: 程序输出文件

### 2. 实现目录规范

#### 允许的文件类型
```
tools/[module_name]/
├── __init__.py          # 模块初始化
├── __main__.py          # 命令行入口
├── cli.py               # 命令行接口
├── [core_modules].py    # 核心功能模块
├── config.yaml          # 配置文件
└── README.md            # 模块文档
```

#### 严禁的文件类型
```
❌ debug_*.py           # Debug脚本
❌ test_*.py            # 测试文件
❌ integration_test.py  # 集成测试
❌ *_test.py            # 任何测试文件
❌ .pytest_cache/       # 测试缓存目录
❌ *.md (除README.md)   # 设计文档和说明文档
```

### 3. Debug代码组织规范

#### Debug目录结构
```
debug/
├── [module_name]/           # 按功能模块组织
│   ├── debug_*.py          # 具体调试脚本
│   └── README.md           # 调试脚本说明
└── README.md               # Debug目录总说明
```

#### Debug脚本命名规范
```python
# ✅ 正确命名
debug_duplicates.py         # 调试重复文件检测
debug_full_merge.py         # 调试完整合并流程
debug_db_status.py          # 调试数据库状态

# ❌ 避免的命名
test_something.py           # 容易与测试混淆
verify_*.py                 # 应该放在tests目录
```

### 4. 测试代码组织规范

#### 测试目录结构
```
tests/
├── tool_[module_name]/     # 按工具模块组织
│   ├── test_*.py          # 单元测试
│   ├── test_data/         # 测试数据
│   └── test_videos/       # 测试视频文件
├── conftest.py            # pytest配置
└── README.md              # 测试说明
```

#### 测试文件命名规范
```python
# ✅ 正确命名
test_video_code_extraction.py    # 功能测试
test_cli.py                      # CLI测试
test_integration.py              # 集成测试

# ❌ 避免的命名
integration_test.py              # 应该用test_前缀
debug_test.py                    # 混淆debug和test概念
```

### 5. 文档组织规范

#### 实现目录文档
- **README.md**: 模块使用说明和API文档
- **禁止**: 设计文档、开发计划、功能说明等

#### 专门文档目录
```
docs/                           # 如需要，可创建专门文档目录
├── design/                     # 设计文档
├── api/                        # API文档
└── development/                # 开发相关文档
```

### 6. 目录清理检查清单

#### 实现目录检查
- [ ] 是否包含debug_*.py文件？
- [ ] 是否包含test_*.py文件？
- [ ] 是否包含.pytest_cache目录？
- [ ] 是否包含设计文档（除README.md外的.md文件）？
- [ ] 是否包含临时文件或输出文件？

#### 迁移步骤
1. **识别文件类型**: 区分实现、测试、debug、文档文件
2. **创建目标目录**: 确保debug/和tests/目录结构正确
3. **移动文件**: 按类型移动到正确位置
4. **更新导入**: 修复移动后的import路径
5. **验证功能**: 确保移动后功能正常

### 7. 最佳实践

#### 开发时的目录管理
```python
# ✅ 正确做法：在debug目录创建调试脚本
# debug/video_info_collector/debug_merge_process.py
from tools.video_info_collector import SmartMergeManager

def debug_merge_logic():
    # 调试代码
    pass

# ❌ 错误做法：在实现目录创建调试脚本
# tools/video_info_collector/debug_merge_process.py
```

#### 测试开发的目录管理
```python
# ✅ 正确做法：在tests目录创建测试
# tests/tool_video_info_collector/test_merge_integration.py
import pytest
from tools.video_info_collector import SmartMergeManager

class TestMergeIntegration:
    # 测试代码
    pass

# ❌ 错误做法：在实现目录创建测试
# tools/video_info_collector/integration_test.py
```

---

## 🧪 测试开发规范

### 1. 强制性测试验证要求
**规则**: 每次代码修改后必须运行完整测试套件，确保所有测试通过后才能提交代码。

**强制执行流程**:
```bash
# 1. 运行完整测试套件
python -m pytest tests/ -v

# 2. 检查测试结果
# ✅ 必须: 所有测试PASSED
# ❌ 禁止: 任何测试FAILED或ERROR
# ⚠️  允许: 测试SKIPPED（但需要说明原因）

# 3. 环境问题处理
# 如果失败是由于环境问题（如psutil架构不兼容），需要：
# - 在代码注释中说明问题原因
# - 确认功能本身正常工作
# - 考虑添加条件跳过或环境检查
```

**测试失败处理原则**:
- **功能性失败**: 必须修复代码，不允许忽略
- **环境性失败**: 需要分析原因，添加适当的环境检查或跳过逻辑
- **测试代码错误**: 修复测试代码，确保测试准确反映功能需求

**历史教训**:
> 之前的`video_code`字段不一致问题就是因为没有在修改后立即运行完整测试套件导致的。
> 如果当时严格执行了测试验证，就能立即发现`search_videos_by_codes`方法名不存在的问题。

### 2. 术语一致性测试要求
**规则**: 每次涉及字段名、方法名、参数名的修改，都必须进行术语一致性检查。

**检查步骤**:
```bash
# 1. 运行术语一致性检查
grep -r "search_code\|vid_code" --include="*.py" .
grep -r "search.*by.*codes[^)]" --include="*.py" .

# 2. 验证命名规范
# - 数据库字段: video_code (不是 code 或 vid_code)
# - 方法名: search_videos_by_video_codes (不是 search_videos_by_codes)
# - CLI参数: --search-video-code (不是 --search-code)

# 3. 运行相关测试
python -m pytest tests/test_cli.py -v -k "search"
python -m pytest tests/test_sqlite_storage.py -v -k "video_code"
```

### 3. 集成测试设计原则

#### 临时文件管理
```python
# ✅ 正确的测试清理策略
@pytest.fixture(autouse=True)
def setup_and_cleanup(self):
    """测试前清理，测试后保留供检查"""
    # 测试开始时清理上次的临时文件
    self._cleanup_temp_dir()
    
    yield
    
    # 测试完成后保留文件供人工检查
    print(f"临时文件保留在: {self.temp_dir_path}")
```

#### 测试数据管理
- 使用专门的 `tests/original_folder` 存放测试数据
- 每次测试从原始数据拷贝到临时目录
- 保持原始测试数据不变

### 2. 测试验证策略

#### 多层次验证
```python
def _validate_results(self):
    """多层次验证测试结果"""
    # 1. 文件数量验证
    assert len(actual_files) == len(expected_files)
    
    # 2. 文件名称验证
    assert actual_files == expected_files
    
    # 3. 特定重命名规则验证
    self._validate_specific_renames()
```

#### 错误处理测试
- 测试工具在无效输入下的行为
- 验证错误信息的准确性
- 确保程序优雅地处理异常情况

---

## 💻 代码风格规范

### 1. Python 代码规范

#### 函数命名
```python
# ✅ 清晰的函数命名
def _cleanup_temp_dir(self):
    """清理临时目录（只在测试开始时调用）"""

def _validate_specific_renames(self):
    """验证特定的重命名规则是否正确应用"""
```

#### 注释规范
```python
# ✅ 详细的注释说明
EXPECTED_RENAMES = {
    "example1.net_TST-002.mp4": "TST-002.mp4",  # 移除 example1.net_
    "TST-001.mp4": "TST-001.mp4",  # 已经是标准格式，不变
    "TST-003-FHD/TST-003-FHD.mp4": "TST-003-FHD/TST-003.mp4",  # 移除 -FHD
}
```

### 2. 测试代码组织

#### 测试类结构
```python
class TestFilenameFormatterIntegration:
    """集成测试类 - 清晰的职责分离"""
    
    # 常量定义
    TEMP_DIR_NAME = "integration_test_temp"
    ORIGINAL_FOLDER = "tests/original_folder"
    
    # 测试数据
    EXPECTED_RENAMES = {...}
    
    # 辅助方法
    def _cleanup_temp_dir(self): ...
    def _copy_original_folder(self): ...
    def _run_filename_formatter(self): ...
    def _validate_results(self): ...
    
    # 测试方法
    def test_complete_integration_workflow(self): ...
    def test_btnets_net_rule_integration(self): ...
```

---

## 📚 经验教训总结

### 1. 配置管理教训

#### 问题描述
在开发集成测试时，发现 `.env` 文件中配置的 `RENAME_RULES_PATH=config/rename_rules.yaml` 指向了不存在的文件。

#### 错误处理方式
为了让测试通过，直接创建了 `config` 目录和 `rename_rules.yaml` 文件。

#### 正确处理方式
应该立即停下来与用户确认：
1. 配置文件的正确位置
2. 是否需要修改 `.env` 配置
3. 项目的配置管理策略

#### 学到的教训
- **永远不要为了通过测试而随意创建文件**
- **遇到配置问题时必须先确认需求**
- **保持项目结构的一致性和简洁性**

### 2. 测试设计教训

#### 问题描述
最初的测试设计在每次测试后都删除临时文件，不便于人工检查结果。

#### 改进方案
- 只在测试开始时清理上次的临时文件
- 测试完成后保留文件供人工验证
- 添加友好的提示信息告知文件位置

#### 学到的教训
- **测试设计要考虑开发者的调试需求**
- **提供清晰的反馈信息**
- **平衡自动化和可观察性**

### 3. 功能重构教训（覆盖功能移除）

#### 问题描述
原始设计中包含了覆盖功能（`--overwrite`），允许覆盖现有文件，但这与工具的安全性原则相冲突。

#### 重构过程
1. **识别问题**: 覆盖功能与"安全重命名"原则冲突
2. **系统性移除**: 从CLI参数、核心逻辑、测试用例中完全移除
3. **测试验证**: 确保移除后所有功能正常
4. **文档更新**: 更新所有相关文档

#### 学到的教训
- **功能设计要与核心原则保持一致**
- **移除功能时要系统性地清理所有相关代码**
- **重构后必须进行全面的回归测试**
- **文档更新是重构的重要组成部分**

### 4. 默认行为优化教训（扁平化默认化）

#### 问题描述
原始设计中扁平化是可选功能（`--flatten`），但用户反馈认为应该是默认行为。

#### 优化过程
1. **需求分析**: 用户认为旧文件夹结构没有保留必要
2. **参数移除**: 移除`--flatten`参数，将扁平化设为默认
3. **测试调整**: 更新所有相关测试用例
4. **文档同步**: 更新CLI帮助和文档说明

#### 学到的教训
- **默认行为应该符合最常见的使用场景**
- **简化CLI参数可以提升用户体验**
- **功能变更需要同步更新测试和文档**
- **用户反馈是优化产品的重要依据**

### 5. 数据脱敏教训（2024年脱敏工作）

#### 问题描述
项目中存在大量敏感数据，包括真实域名和敏感视频编号，这些数据分布在测试文件、配置文件、文档和示例代码中，影响了项目的安全性和可分享性。

> ⚠️ **安全提示**: 具体的敏感信息示例请参考 `SECURITY.example` 文档

#### 脱敏过程
1. **系统性扫描**: 使用正则表达式扫描所有文件中的敏感数据
2. **分类处理**: 区分测试代码、配置文件、文档、输出文件等不同类型
3. **批量替换**: 制定统一的替换规则进行批量处理
4. **功能验证**: 确保脱敏后所有测试通过，功能正常
5. **文档同步**: 更新所有相关文档和示例

#### 发现的问题
- **分布广泛**: 敏感数据散布在多个文件类型中，包括 `.py`、`.yaml`、`.md`、`.csv` 等
- **隐蔽性强**: 一些敏感数据隐藏在测试用例的断言中，不易发现
- **关联复杂**: 修改敏感数据后需要同步更新相关的测试期望值
- **遗漏风险**: 手动查找容易遗漏，需要系统性的扫描工具

#### 具体脱敏工作
```bash
# 域名脱敏（具体模式见SECURITY.example）
[敏感域名1] → example1.net
[敏感域名2] → site1234.com  
[敏感域名3] → test2222.xyz

# 视频编号脱敏（具体模式见SECURITY.example）
[敏感前缀1][数字] → TEST[数字]
[敏感前缀2][数字] → DEMO[数字]
[敏感前缀3][数字] → SAMPLE[数字]

# 涉及文件类型
- 测试文件: test_*.py (75个测试用例)
- 配置文件: rename_rules.yaml (38条规则)
- 文档文件: *.md (示例和说明)
- 输出文件: *.csv (演示数据)
```

#### 学到的教训
- **预防优于治理**: 从项目开始就应该使用通用示例数据
- **系统性扫描**: 必须使用工具进行全面扫描，不能依赖人工查找
- **一致性原则**: 脱敏替换规则要保持一致，便于维护和理解
- **验证重要性**: 脱敏后必须进行完整的功能测试验证
- **文档同步**: 代码脱敏的同时必须同步更新所有相关文档
- **团队意识**: 需要建立团队的数据安全意识和脱敏规范

### 6. 依赖管理教训（2024年依赖维护工作）

#### 问题描述
项目使用Poetry管理依赖，但pyproject.toml中缺少重要的依赖包声明，包括：
- 测试相关依赖：`pytest-cov`、`pytest-mock`、`pytest-xdist`
- 系统依赖说明：`FFmpeg`、`SQLite3`
- 项目元数据不完整

#### 解决过程
1. **全面依赖分析**: 扫描所有Python文件的import语句
2. **分类整理**: 区分Python标准库、第三方包、系统依赖
3. **配置更新**: 系统性更新pyproject.toml配置
4. **文档同步**: 更新所有相关文档的依赖说明
5. **验证测试**: 确保依赖配置正确且测试通过

#### 发现的问题
- **隐性依赖**: 代码中使用了未在配置中声明的包
- **系统依赖缺失**: FFmpeg通过subprocess调用，但文档中未说明
- **测试依赖不全**: 缺少覆盖率和并行测试插件
- **元数据不完整**: 缺少项目描述、关键词、分类器等

#### 学到的教训
- **依赖声明必须完整**: 所有使用的第三方包都要在配置中声明
- **系统依赖需要文档化**: 外部工具依赖必须在安装文档中说明
- **定期依赖审查**: 每次功能更新后都要检查依赖变化
- **测试环境一致性**: 开发、测试、生产环境的依赖要保持一致
- **文档同步更新**: 依赖变更必须同步更新所有相关文档

### 7. 运行与日志检查教训（2025-11-07 Streamlit 崩溃）

#### 问题描述
在将页面切换由顶部按钮改为侧边栏导航后，未在宣布完成前检查终端日志，导致服务启动时报错并崩溃：

```
streamlit.errors.StreamlitDuplicateElementKey: There are multiple elements with the same `key='sidebar_route'`.
```

根因：同一轮渲染中重复创建了带相同 `key` 的侧边栏控件（在多个位置调用侧边栏渲染）。

#### 正确处理方式
1. 立即停止服务，审查并修复重复渲染：仅在 `main()` 中渲染侧边栏，并增加一次性渲染哨兵（`st.session_state["_sidebar_nav_rendered"]`）。
2. 重启服务并再次检查终端输出，确认无错误栈。
3. 打开预览地址（如 `http://localhost:8501/`）进行可视验证。
4. 将本次事故记录进《开发守则》，形成强制流程规范。

#### 学到的教训
- **宣布完成前必须检查终端日志**：任何服务启动或命令执行后，先看是否有错误或异常栈。
- **避免重复控件 key**：Streamlit 等 UI 框架要求每个控件 `key` 唯一；同一轮渲染严禁重复创建同一控件。
- **修复-重启-验证三步走**：修复代码后重启服务、检查日志、打开预览进行端到端确认。

#### 强制执行流程（运行与日志检查原则）
> 自本次事件起，以下流程为强制要求，违背则视为任务未完成。

1. 启动或执行后检查终端日志：
   - 关注关键字：`Traceback`、`Exception`、`ERROR`、`CRITICAL`、`Duplicate`
   - 对于 Streamlit，确保出现启动横幅且无运行期异常栈。
2. Web 服务健康检查（示例）：
   - `curl -sSf --max-time 3 http://localhost:8501/ >/dev/null && echo "OK" || echo "FAIL"`
3. 预览验证：
   - 打开本地预览地址（如 `http://localhost:8501/`），实际点击页面交互，确认关键功能路径正常。
4. 变更后回归测试：
   - `pytest tests/ -q` 或项目既定测试命令，全部通过后方可汇报完成。
5. 只保留一个服务器进程：
   - 若需重启，先停止旧进程再启动，避免端口占用或状态混乱。

#### 示例（Streamlit）
```bash
# 启动服务器（macOS）
python3 -m streamlit run ui/app.py --server.port 8501 --server.headless true

# 健康检查（3秒内成功返回）
curl -sSf --max-time 3 http://localhost:8501/ >/dev/null && echo "OK" || echo "FAIL"

# 运行完整测试套件
pytest tests/ -q
```

---

## ⚠️ 反面教材与改进

### 1. 配置文件管理反面教材

#### ❌ 错误做法
```bash
# 发现 config/rename_rules.yaml 不存在
# 直接创建文件和目录
mkdir config
cp tools/filename_formatter/rename_rules.yaml config/
```

#### ✅ 正确做法
```bash
# 发现配置问题时
# 1. 停下来分析问题
# 2. 与用户确认正确做法
# 3. 修正 .env 配置
RENAME_RULES_PATH=tools/filename_formatter/rename_rules.yaml
```

### 2. 测试清理策略反面教材

#### ❌ 错误做法
```python
def teardown(self):
    """测试后立即删除所有临时文件"""
    shutil.rmtree(self.temp_dir_path)  # 无法人工检查结果
```

#### ✅ 正确做法
```python
def setup_and_cleanup(self):
    """智能的清理策略"""
    # 只清理上次的文件
    self._cleanup_temp_dir()
    yield
    # 保留本次结果供检查
    print(f"临时文件保留在: {self.temp_dir_path}")
```

### 3. 功能设计一致性反面教材

#### ❌ 错误做法
```python
# 同时提供覆盖和安全重命名功能
def rename_file(src, dst, overwrite=False):
    if overwrite or not dst.exists():
        src.rename(dst)  # 可能覆盖现有文件
```

#### ✅ 正确做法
```python
# 坚持安全重命名原则
def rename_file(src, dst, conflict_resolution="skip"):
    if dst.exists():
        if conflict_resolution == "skip":
            return "skipped: target exists"
        elif conflict_resolution == "rename":
            dst = generate_unique_name(dst)
    src.rename(dst)  # 绝不覆盖现有文件
```

### 4. 默认行为设计反面教材

#### ❌ 错误做法
```python
# 让用户为常见需求添加额外参数
parser.add_argument('--flatten', action='store_true', 
                   help='将文件移动到根目录')  # 大多数用户都需要这个功能
```

#### ✅ 正确做法
```python
# 将最常见的需求设为默认行为
# 扁平化默认启用，简化用户操作
flatten_output = True  # 默认行为
# 如果需要，可以添加 --no-flatten 选项
```

### 5. 数据脱敏反面教材

#### ❌ 错误做法
```python
# 在测试代码中直接使用真实敏感数据
def test_rename_rules(self):
    input_file = "[敏感域名]_[敏感编号].mp4"  # 真实域名和敏感编号
    expected = "[敏感编号].mp4"
    assert formatter.format_filename(input_file) == expected

# 在配置文件中使用真实数据
rename_rules:
  - pattern: "[敏感域名]_"  # 真实域名
    replace: ""
  - pattern: "[敏感前缀]"        # 敏感前缀
    replace: "TEST"
```

#### ✅ 正确做法
```python
# 使用通用示例数据
def test_rename_rules(self):
    input_file = "example1.net_TEST-896.mp4"  # 通用域名和测试编号
    expected = "TEST-896.mp4"
    assert formatter.format_filename(input_file) == expected

# 在配置文件中使用示例数据
rename_rules:
  - pattern: "example1.net_"  # 示例域名
    replace: ""
  - pattern: "TEST"           # 通用前缀
    replace: "DEMO"
```

#### ❌ 错误的脱敏方式
```bash
# 手动逐个查找和替换，容易遗漏
grep "[敏感域名]" file1.py
sed -i 's/[敏感域名]/example1.net/' file1.py
# 忘记检查其他文件...

# 不验证脱敏后的功能
# 直接替换后不运行测试，导致功能异常
```

#### ✅ 正确的脱敏方式
```bash
# 系统性扫描所有文件（具体模式见SECURITY.example）
grep -r "[敏感域名模式]" .
find . -type f \( -name "*.py" -o -name "*.yaml" -o -name "*.md" \) \
  -exec grep -l "[敏感域名模式]" {} \;

# 批量替换并验证
find . -type f -name "*.py" -exec sed -i 's/[敏感域名模式]/example1.net/g' {} +
pytest tests/ -v  # 验证功能正常
```

#### ❌ 错误的文档处理
```markdown
# 在文档中保留敏感示例
## 使用示例
输入: [敏感域名]_[敏感编号].mp4
输出: [敏感编号].mp4

# 在README中展示真实数据
支持的网站: [敏感域名1], [敏感域名2]
```

#### ✅ 正确的文档处理
```markdown
# 使用通用示例
## 使用示例
输入: example1.net_TEST-896.mp4
输出: TEST-896.mp4

# 在README中使用示例数据
支持的网站: example1.net, site1234.com
```

### 6. 依赖管理反面教材

#### ❌ 错误做法
```toml
# pyproject.toml 中依赖不完整
[project]
dependencies = [
    "python-dotenv",
    "pyyaml",
    # 缺少实际使用的测试依赖
]

# 没有说明系统依赖
# 代码中使用subprocess调用ffprobe，但未在文档中说明
```

#### ✅ 正确做法
```toml
# pyproject.toml 中完整的依赖声明
[project]
dependencies = [
    "python-dotenv>=0.19.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.10",
    "pytest-xdist>=3.0",
]

# 在README.md和HANDOVER.md中明确说明系统依赖
### 系统依赖
- FFmpeg (ffprobe): 用于视频元数据提取
- SQLite3: 数据库存储支持
```

#### ❌ 错误的依赖分析方式
```bash
# 仅凭记忆添加依赖，不进行系统性分析
# 忽略import语句扫描
# 不区分运行时依赖和开发依赖
```

#### ✅ 正确的依赖分析方式
```bash
# 系统性扫描所有import语句
grep -r "^import\|^from.*import" --include="*.py" .

# 分类整理依赖
# 1. Python标准库 (json, os, subprocess等)
# 2. 第三方Python包 (pytest, yaml等)  
# 3. 系统依赖 (ffmpeg, sqlite3等)

# 验证依赖配置
poetry check
poetry install --with dev
pytest -q  # 确保测试通过
```

---

## 🚀 最佳实践总结

### 1. 开发流程最佳实践
1. **需求确认**: 遇到不确定的需求时，立即与用户确认
2. **最小修改**: 优先使用现有文件和配置
3. **渐进开发**: 先实现核心功能，再完善细节
4. **及时验证**: 每个阶段都要验证功能正确性

### 2. 测试开发最佳实践
1. **数据隔离**: 使用专门的测试数据目录
2. **结果保留**: 保留测试结果供人工验证
3. **多层验证**: 从多个角度验证测试结果
4. **错误处理**: 测试异常情况和边界条件

### 3. 代码质量最佳实践
1. **清晰命名**: 函数和变量名要表达明确的意图
2. **详细注释**: 解释复杂逻辑和业务规则
3. **职责分离**: 每个函数只做一件事
4. **一致性**: 保持代码风格和项目结构的一致性

### 4. 功能重构最佳实践
1. **原则一致性**: 确保所有功能与核心设计原则保持一致
2. **系统性清理**: 移除功能时要清理所有相关代码、测试、文档
3. **用户体验优先**: 将最常用的功能设为默认行为
4. **安全第一**: 在便利性和安全性之间，优先选择安全性
5. **全面测试**: 重构后必须进行完整的回归测试
6. **文档同步**: 代码变更必须同步更新所有相关文档

### 5. 依赖管理最佳实践
1. **完整性原则**: 所有使用的依赖都必须在配置文件中明确声明
2. **分类管理**: 严格区分运行依赖、开发依赖、测试依赖和系统依赖
3. **版本策略**: 使用语义化版本范围，平衡稳定性和更新能力
4. **定期审查**: 每次功能更新后都要检查和更新依赖配置
5. **文档同步**: 依赖变更必须同步更新安装文档和交接文档
6. **环境一致**: 确保开发、测试、生产环境的依赖配置一致
7. **工具辅助**: 使用Poetry等工具进行依赖解析和冲突检测
8. **系统依赖**: 外部工具依赖必须在文档中说明安装方式

---

## 📝 检查清单

### 开发前检查
- [ ] 需求是否明确？
- [ ] 配置路径是否正确？
- [ ] 是否需要创建新文件？
- [ ] 项目结构是否合理？

### 开发中检查
- [ ] 是否遵循现有的代码风格？
- [ ] 是否使用了现有的工具和库？
- [ ] 是否添加了必要的注释？
- [ ] 是否考虑了错误处理？

### 开发后检查
- [ ] 功能是否正确实现？
- [ ] 测试是否全部通过？
- [ ] 是否有不必要的文件创建？
- [ ] 文档是否需要更新？

### 功能重构检查
- [ ] 重构是否与核心原则一致？
- [ ] 是否系统性地清理了所有相关代码？
- [ ] 是否更新了所有相关测试用例？
- [ ] 是否更新了CLI帮助和文档？
- [ ] 是否进行了完整的回归测试？
- [ ] 默认行为是否符合用户期望？

### 数据脱敏检查
- [ ] 是否扫描了所有文件中的敏感数据？
- [ ] 是否使用正则表达式进行系统性检查？
- [ ] 测试文件中是否使用通用示例数据？
- [ ] 配置文件中是否移除了真实域名和标识？
- [ ] 文档和示例中是否使用了脱敏数据？
- [ ] 脱敏后是否运行了完整的测试验证？
- [ ] 是否检查了输出文件和日志中的敏感信息？
- [ ] 是否建立了敏感词汇表和检查规范？

### 依赖管理检查
- [ ] 是否扫描了所有import语句？
- [ ] 是否区分了运行依赖和开发依赖？
- [ ] 是否在pyproject.toml中声明了所有第三方包？
- [ ] 是否在文档中说明了系统依赖的安装方式？
- [ ] 是否使用了合适的版本约束策略？
- [ ] 是否运行了poetry check验证配置？
- [ ] 是否更新了README.md和HANDOVER.md中的依赖说明？
- [ ] 是否验证了依赖配置后测试仍能通过？

---

## 📖 相关文档

### 文档体系说明
本项目包含两份核心开发文档，各有不同的定位和作用：

#### DEVELOPMENT_GUIDELINES.md (本文档)
- **定位**: 开发规范与经验教训
- **内容**: 具体的开发原则、规范、最佳实践和反面教材
- **受众**: 开发团队成员，用于日常开发指导
- **更新频率**: 随着项目经验积累持续更新

#### DEVELOPMENT_OUTLINE.md
- **定位**: 项目开发纲要
- **内容**: 项目概述、技术栈、架构设计、功能说明、扩展路线
- **受众**: 新成员了解项目、项目规划和决策
- **更新频率**: 项目重大变更时更新

### 文档使用建议
1. **新成员入门**: 先阅读 `DEVELOPMENT_OUTLINE.md` 了解项目全貌
2. **日常开发**: 参考 `DEVELOPMENT_GUIDELINES.md` 遵循开发规范
3. **问题解决**: 在 `DEVELOPMENT_GUIDELINES.md` 中查找相关经验教训
4. **项目规划**: 参考 `DEVELOPMENT_OUTLINE.md` 中的扩展路线和架构设计

### 文档维护原则
- 保持两份文档的独立性和互补性
- 避免内容重复，确保各自专注于不同层面
- 定期检查文档间的一致性和关联性
- 根据项目发展适时调整文档结构和内容

---

*本文档基于 filename_formatter 工具开发过程中的实际经验总结，包括集成测试开发、功能重构、数据脱敏等多个方面的经验教训，旨在为后续开发提供指导和参考。*