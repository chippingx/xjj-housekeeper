# Video Info Collector

视频文件信息收集工具，**批量收集视频文件元数据，支持标签管理和数据持久化**。提供临时收集和持久化存储的两阶段工作流，适用于大规模视频文件库管理。

## 功能概览

- **📊 视频元数据收集** - 自动提取文件名、创建时间、文件大小、视频时长等信息
- **🏷️ 灵活标签系统** - 支持多标签管理，10字以内的文字描述
- **📍 路径信息管理** - 手动输入和管理视频文件的逻辑路径信息
- **📝 两阶段存储** - 临时收集文件 + 持久化主数据库，支持预览和确认
- **🔄 增量更新** - 支持对已有记录的更新和追加
- **💾 轻量级存储** - 基于文本文件的存储方案，支持上万条记录

## 核心特性

### 1. 视频信息收集
- **文件名**: 完整文件名（含扩展名）
- **创建时间**: 文件系统创建时间
- **文件大小**: 格式化显示（如 5.23G、5G）
- **视频时长**: 通过视频元数据提取（HH:MM:SS格式）
- **文件路径**: 相对于扫描根目录的路径

### 2. 标签管理系统
- **多标签支持**: 每个视频可以有多个标签
- **标签限制**: 每个标签最多10个字符
- **分隔符规则**: 使用分号(;)分隔多个标签
- **标签内容限制**: 标签内容不能包含分号(;)字符
- **手动管理**: 在收集时可选择性添加标签
- **标签验证**: 自动验证标签格式和长度

### 3. 路径信息管理
- **逻辑路径**: 用户自定义的逻辑分类路径
- **手动输入**: 类似标签的手动管理方式
- **路径层级**: 支持多层级路径结构

## CLI 用法

### 基本用法
```bash
# 收集指定目录的视频信息到临时文件
python -m tools.video_info_collector /path/to/videos

# 指定标签收集（使用分号分隔）
python -m tools.video_info_collector /path/to/videos --tags "动作片;高清;2024"

# 指定逻辑路径
python -m tools.video_info_collector /path/to/videos --path "电影/动作片/2024"
```

### 高级用法
```bash
# 指定临时文件名
python -m tools.video_info_collector /path/to/videos --temp-file temp_collection.csv

# 预览模式（不写入文件）
python -m tools.video_info_collector /path/to/videos --dry-run

# 递归扫描子目录
python -m tools.video_info_collector /path/to/videos --recursive

# 指定视频格式过滤
python -m tools.video_info_collector /path/to/videos --extensions .mp4,.mkv,.avi

# 输出格式选择
python -m tools.video_info_collector /path/to/videos --output-format csv  # 默认
python -m tools.video_info_collector /path/to/videos --output-format sqlite  # 直接输出SQLite
```

### 数据合并
```bash
# 将临时CSV文件合并到SQLite数据库
python -m tools.video_info_collector --merge temp_collection.csv

# 指定主数据库文件
python -m tools.video_info_collector --merge temp_collection.csv --database output/video_info_collector/database/video_database.db

# 合并时处理重复项
python -m tools.video_info_collector --merge temp_collection.csv --duplicate-strategy update

# 从SQLite导出为CSV
python -m tools.video_info_collector --export output/video_info_collector/database/video_database.db --format csv --output output/video_info_collector/csv/exported_data.csv
```

### 视频查询功能
```bash
# 通过视频code查询（文件名去掉后缀）
python -m tools.video_info_collector --search-code "ABC-123"

# 查询多个视频code（逗号分隔）
python -m tools.video_info_collector --search-code "ABC-123,DEF-456"

# 查询多个视频code（空格分隔）
python -m tools.video_info_collector --search-code "ABC-123 DEF-456"

# 指定数据库文件进行查询
python -m tools.video_info_collector --search-code "ABC-123" --database custom_database.db
```

**查询功能特性**:
- 🔍 **精确匹配**: 基于文件名（去掉扩展名）进行精确查询
- 📋 **简洁输出**: 只显示视频code、文件大小、逻辑路径三个关键字段
- 🔤 **大小写不敏感**: 自动忽略大小写差异
- 🧹 **自动清理**: 自动去除前后空格
- 📊 **多查询支持**: 支持同时查询多个视频code

### 数据统计功能
```bash
# 显示基本统计信息
python -m tools.video_info_collector stats --type basic

# 按标签分组统计
python -m tools.video_info_collector stats --type tags

# 按分辨率分组统计
python -m tools.video_info_collector stats --type resolution

# 按时长分组统计
python -m tools.video_info_collector stats --type duration

# 显示增强统计信息（包含平均值等）
python -m tools.video_info_collector stats --type enhanced

# 指定数据库文件进行统计
python -m tools.video_info_collector stats --type basic --database custom_database.db
```

**统计功能特性**:
- 📊 **多维度统计**: 支持基本、标签、分辨率、时长、增强等多种统计类型
- 📈 **美观表格**: 使用表格格式清晰展示统计结果
- 🔢 **详细数据**: 包含总数、总大小、总时长、平均值等详细信息
- 🏷️ **标签分析**: 按标签分组显示视频数量分布
- 📐 **分辨率分析**: 按分辨率分组统计视频质量分布
- ⏱️ **时长分析**: 按时长范围分组统计视频长度分布

### 可用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `directory` | 要扫描的目录路径 | 必需 |
| `--tags` | 为所有文件添加的标签（分号分隔） | 无 |
| `--path` | 逻辑路径信息 | 无 |
| `--temp-file` | 临时收集文件名 | `output/video_info_collector/csv/temp_video_info_{timestamp}.csv` |
| `--output-format` | 输出格式：csv/sqlite | `csv` |
| `--dry-run` | 预览模式，不写入文件 | False |
| `--recursive` | 递归扫描子目录 | True |
| `--extensions` | 视频文件扩展名过滤 | `.mp4,.mkv,.avi,.mov,.wmv,.flv` |
| `--merge` | 合并临时文件到主数据库 | 无 |
| `--database` | 主数据库文件路径 | `output/video_info_collector/database/video_database.db` |
| `--duplicate-strategy` | 重复项处理策略：skip/update/append | `skip` |
| `--export` | 从SQLite导出数据 | 无 |
| `--format` | 导出格式：csv/json | `csv` |
| `--output` | 导出文件路径 | 无 |
| `--search-code` | 通过视频code查询（支持多个，逗号或空格分隔） | 无 |
| `stats` | 统计子命令 | 无 |
| `--type` | 统计类型：basic/tags/resolution/duration/enhanced | `basic` |

## 数据格式设计

### 临时收集文件格式 (CSV)
**文件名**: `output/video_info_collector/csv/temp_video_info_{timestamp}.csv`

```csv
filename,file_path,file_size,file_size_bytes,created_time,duration,duration_seconds,tags,logical_path,scan_time,scan_directory
movie_example.mp4,action/2024/movie_example.mp4,2.45G,2630000000,2024-01-15T10:30:00,01:45:30,6330,"动作片;高清",电影/动作片/2024,2024-01-20T15:45:00,/path/to/videos
action_movie.mkv,action/2024/action_movie.mkv,3.21G,3447000000,2024-01-16T14:20:00,02:15:45,8145,"动作片;4K;2024",电影/动作片/2024,2024-01-20T15:45:00,/path/to/videos
```

**优点**:
- 📊 Excel/Numbers 直接打开编辑
- 🌐 浏览器可直接查看
- ✏️ 易于手动编辑标签和路径
- 📈 支持数据透视表分析

### 主数据库文件格式 (SQLite)
**文件名**: `output/video_info_collector/database/video_database.db`

#### 主表结构 (video_info)
```sql
CREATE TABLE video_info (
    id TEXT PRIMARY KEY,                    -- SHA256哈希 (文件路径+大小)
    filename TEXT NOT NULL,                 -- 文件名
    file_path TEXT NOT NULL,                -- 相对路径
    file_size TEXT NOT NULL,                -- 格式化大小 (如 2.45G)
    file_size_bytes INTEGER NOT NULL,       -- 字节大小
    created_time TEXT NOT NULL,             -- 文件创建时间
    duration TEXT,                          -- 时长 (HH:MM:SS)
    duration_seconds INTEGER,               -- 时长秒数
    logical_path TEXT,                      -- 逻辑路径
    first_scan_time TEXT NOT NULL,          -- 首次扫描时间
    last_update_time TEXT NOT NULL,         -- 最后更新时间
    scan_count INTEGER DEFAULT 1            -- 扫描次数
);
```

#### 标签表 (video_tags)
```sql
CREATE TABLE video_tags (
    video_id TEXT NOT NULL,                 -- 关联video_info.id
    tag TEXT NOT NULL,                      -- 标签内容
    created_time TEXT NOT NULL,             -- 标签创建时间
    PRIMARY KEY (video_id, tag),
    FOREIGN KEY (video_id) REFERENCES video_info(id)
);
```

#### 扫描历史表 (scan_history)
```sql
CREATE TABLE scan_history (
    video_id TEXT NOT NULL,                 -- 关联video_info.id
    scan_directory TEXT NOT NULL,           -- 扫描目录
    scan_time TEXT NOT NULL,                -- 扫描时间
    PRIMARY KEY (video_id, scan_directory, scan_time),
    FOREIGN KEY (video_id) REFERENCES video_info(id)
);
```

**优点**:
- 🗄️ 结构化存储，支持复杂查询
- 🔍 高效的索引和搜索
- 🌐 浏览器插件 (如 SQLite Viewer) 可直接查看
- 📊 支持 SQL 分析和报表
- 💾 文件大小优化，适合大量数据

## 工作流程

### 1. 信息收集阶段
1. 扫描指定目录的视频文件
2. 提取视频元数据（文件大小、时长等）
3. 应用用户指定的标签和路径信息
4. 写入临时收集文件（**CSV格式**，便于Excel/浏览器查看）
5. 显示收集统计信息

### 2. 预览确认阶段
1. 用户用 **Excel/Numbers/浏览器** 查看临时CSV文件
2. 直接在表格中编辑标签、路径等信息
3. 利用表格软件的排序、筛选功能进行数据整理
4. 验证数据格式和完整性

### 3. 数据合并阶段
1. 读取临时CSV文件
2. 与SQLite主数据库进行重复项检查
3. 根据策略处理重复项（跳过/更新/追加）
4. 将数据写入 **SQLite数据库**（结构化存储）
5. 自动创建索引以优化查询性能
6. 生成合并报告

### 4. 数据查看和分析
1. 使用浏览器插件（如 SQLite Viewer）查看数据库
2. 执行SQL查询进行数据分析
3. 导出为CSV格式进行进一步分析
4. 利用数据透视表等工具生成报表

## 技术实现方案

### 视频元数据提取
- **推荐方案**: 使用 `ffprobe` (FFmpeg工具链)
  - 优点：功能强大，支持所有主流视频格式
  - 缺点：需要系统安装FFmpeg
- **备选方案**: 使用 `moviepy` Python库
  - 优点：纯Python实现，易于安装
  - 缺点：性能较低，依赖较重

### 数据存储格式
- **临时存储**: CSV格式，便于表格软件编辑和浏览器查看
- **持久存储**: SQLite数据库，支持复杂查询和高效索引
- **优点**: 
  - CSV: 通用性强、易编辑、支持数据透视表
  - SQLite: 无需安装、支持SQL、文件大小优化
- **适用场景**: 从几百到几万条记录的各种规模数据

### 重复项检测
- **主键设计**: 基于文件路径和大小的SHA256哈希
- **SQLite索引**: 自动为主键和常用查询字段创建索引
- **检测策略**: 
  - 文件路径 + 文件大小 → 相同文件
  - 仅文件名 + 文件大小 → 可能的重复文件
- **性能优化**: 使用SQLite的UPSERT语句高效处理重复项

### 数据库设计优势
- **规范化存储**: 标签和扫描历史分表存储，避免数据冗余
- **查询性能**: 支持复杂的JOIN查询和聚合分析
- **数据完整性**: 外键约束确保数据一致性
- **扩展性**: 易于添加新字段和表结构

## 配置文件

### config.yaml
```yaml
# 视频文件扩展名配置
video_extensions:
  - .mp4
  - .mkv
  - .avi
  - .mov
  - .wmv
  - .flv
  - .m4v
  - .webm

# 文件大小格式化配置
size_format:
  precision: 2  # 小数位数
  units: ["B", "K", "M", "G", "T"]

# 标签验证配置
tags:
  max_length: 10
  max_count: 10
  forbidden_chars: ["/", "\\", ":", "*", "?", "\"", "<", ">", "|"]

# 数据库配置
database:
  default_name: "video_database.db"
  backup_enabled: true
  backup_count: 5
  sqlite_settings:
    journal_mode: "WAL"  # Write-Ahead Logging for better performance
    synchronous: "NORMAL"  # Balance between safety and speed
    cache_size: 10000  # Cache size in pages
    temp_store: "MEMORY"  # Store temporary tables in memory
  csv_settings:
    encoding: "utf-8-sig"  # Excel compatible encoding
    delimiter: ","
    quoting: "minimal"  # Only quote when necessary

# FFmpeg配置
ffmpeg:
  timeout: 30  # 秒
  fallback_enabled: true  # 启用moviepy备选方案
```

## 示例输出

### 收集阶段输出
```
正在扫描目录: /path/to/videos
支持的视频格式: .mp4, .mkv, .avi, .mov, .wmv, .flv
递归扫描: 是
应用标签: ["动作片", "高清"]
逻辑路径: "电影/动作片/2024"

扫描进度: [████████████████████████████████] 100% (150/150 文件)

收集完成:
- 总文件数: 150
- 视频文件: 45
- 总大小: 125.6G
- 平均时长: 01:32:15
- 临时文件: output/video_info_collector/csv/temp_video_info_20240120_154500.csv

请用Excel/Numbers/浏览器查看临时文件内容，确认无误后执行合并操作。
```

### 合并阶段输出
```
正在合并临时文件: output/video_info_collector/csv/temp_video_info_20240120_154500.csv
目标数据库: output/video_info_collector/database/video_database.db
重复策略: skip

合并进度: [████████████████████████████████] 100% (45/45 记录)

合并完成:
- 新增记录: 38
- 跳过重复: 7
- 更新记录: 0
- 数据库总记录: 1,247
- 备份文件: video_database_backup_20240120_154600.db
- 可用工具: SQLite Viewer (浏览器插件) 或 DB Browser for SQLite
```

## 安全特性与保证

### 🔒 核心安全保证

经过全面的安全性检查和测试，本工具提供以下安全保证：

#### 1. **文件安全保证**
- ✅ **无文件删除风险**: 工具只读取视频文件信息，绝不删除任何原始文件
- ✅ **无文件覆盖风险**: 输出文件采用安全的覆盖策略，SQLite使用upsert更新现有记录
- ✅ **只读扫描**: 对原始视频文件进行只读访问，不修改文件内容或属性

#### 2. **数据库安全保证**
- ✅ **SQL注入防护**: 所有数据库操作使用参数化查询，完全防止SQL注入攻击
- ✅ **事务完整性**: 适当使用数据库事务，确保数据一致性
- ✅ **数据完整性**: 外键约束和索引确保数据关系的完整性

#### 3. **幂等性保证**
- ✅ **重复执行安全**: 对同一目录多次执行扫描不会产生重复数据
- ✅ **增量更新**: 自动识别已存在的文件，只更新变化的信息
- ✅ **扫描历史追踪**: 记录每次扫描历史，支持审计和回溯

#### 4. **路径安全保证**
- ✅ **基础路径遍历防护**: 依赖系统权限防止恶意路径访问
- ✅ **输出路径验证**: 输出文件路径受系统权限控制
- ✅ **目录访问控制**: 只能访问有权限的目录

### 🛡️ 安全测试覆盖

本工具包含完整的安全性测试用例，确保以下安全功能不被破坏：

- **文件删除风险测试**: 验证工具不会删除任何文件
- **幂等性测试**: 验证重复执行的安全性和一致性
- **路径遍历攻击测试**: 验证对恶意路径的防护能力
- **数据库安全测试**: 验证SQL注入防护和事务完整性

### 🔧 传统安全特性

1. **数据备份**: 自动备份主数据库文件
2. **格式验证**: 严格的数据格式验证
3. **错误恢复**: 支持从备份文件恢复
4. **增量处理**: 支持中断后继续处理
5. **权限控制**: 遵循系统文件权限设置

## 扩展性设计

### 插件系统
- **元数据提取器**: 支持不同的视频元数据提取方案
- **存储后端**: 支持不同的数据存储格式
- **标签处理器**: 支持自定义标签验证和处理逻辑

### 未来功能
- **Web界面**: 基于Web的数据浏览和管理界面
- **数据导出**: 支持导出为CSV、Excel等格式
- **高级搜索**: 基于标签、时长、大小等的复合搜索
- **重复文件检测**: 基于内容哈希的重复文件检测
- **批量标签操作**: 批量添加、删除、修改标签

## 常见问题

**Q: 支持哪些视频格式？**
A: 默认支持 .mp4, .mkv, .avi, .mov, .wmv, .flv 等主流格式，可通过配置文件自定义。

**Q: 如何处理大文件或损坏的视频文件？**
A: 工具会设置超时机制，对于无法处理的文件会记录错误信息并跳过。

**Q: 临时文件可以手动编辑吗？**
A: 可以，临时文件采用CSV格式，可以用Excel、Numbers或任何表格软件直接编辑标签、路径等信息。

**Q: 如何查看SQLite数据库？**
A: 推荐使用浏览器插件"SQLite Viewer"或下载"DB Browser for SQLite"。也可以导出为CSV格式查看。

**Q: 如何处理文件移动后的记录更新？**
A: 建议重新扫描并使用update策略合并，工具会根据文件大小和名称识别相同文件。

**Q: CSV文件在Excel中显示乱码怎么办？**
A: 工具默认使用UTF-8-BOM编码，确保Excel正确显示中文。如仍有问题，可在Excel中选择"数据"->"从文本"导入。

**Q: SQLite数据库文件过大怎么办？**
A: SQLite支持数十GB的数据，如需要可以使用VACUUM命令压缩，或按时间/类别分割数据库。

---

*本工具设计遵循xjj_housekeeper项目的设计原则，注重安全性、易用性和可扩展性。*