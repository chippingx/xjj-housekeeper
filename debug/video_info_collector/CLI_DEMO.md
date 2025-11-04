# Video Info Collector CLI 演示

这个文档展示了如何使用 Video Info Collector 的命令行界面。

## 安装和设置

确保你在项目根目录下，并且已经安装了所需的依赖：

```bash
cd /path/to/xjj_housekeeper
pip install -r requirements.txt
```

## 推荐工作流程（安全且可控）

### 第一步：数据库初始化

如果是第一次使用或需要重置数据库，请先初始化数据库：

```bash
# 初始化/重置默认数据库
python -m tools.video_info_collector --init-db

# 初始化/重置自定义数据库
python -m tools.video_info_collector --init-db --database /path/to/custom.db

# 为不同项目创建独立的数据库
python -m tools.video_info_collector --init-db --database projects/movie_collection.db
python -m tools.video_info_collector --init-db --database projects/tv_series.db
```

**数据库初始化功能特性：**
- 🔄 **重置现有数据库**：删除所有数据并重新创建表结构
- 🆕 **创建新数据库**：如果数据库文件不存在，自动创建
- 🛡️ **安全确认**：重置现有数据库时需要输入 "yes" 确认
- 📁 **自动创建目录**：自动创建数据库文件所在的目录
- ✅ **表结构验证**：确保数据库包含正确的表结构

### 第二步：基于目录生成CSV文件

**强烈建议**：先生成CSV文件，人工检查内容后再导入数据库。这样可以避免错误数据污染数据库。

```bash
# 扫描指定目录，输出到CSV文件
python -m tools.video_info_collector /path/to/videos --output my_videos.csv

# 添加标签和逻辑路径信息
python -m tools.video_info_collector /path/to/videos --output my_videos.csv --tags "电影,高清" --path "媒体库/电影/2024"

# 扫描多个目录到不同的CSV文件
python -m tools.video_info_collector /media/movies --output movies.csv --tags "电影" --path "媒体库/电影"
python -m tools.video_info_collector /media/tv_shows --output tv_shows.csv --tags "电视剧" --path "媒体库/电视剧"
python -m tools.video_info_collector /media/documentaries --output documentaries.csv --tags "纪录片" --path "媒体库/纪录片"
```

**人工检查建议：**
1. 打开生成的CSV文件，检查文件路径是否正确
2. 确认视频信息（分辨率、时长等）是否合理
3. 验证标签和逻辑路径是否符合预期
4. 删除或修正任何错误的记录

### 第三步：CSV合并到数据库

确认CSV文件内容无误后，将其合并到数据库：

```bash
# 合并单个CSV文件到数据库
python -m tools.video_info_collector --merge my_videos.csv

# 合并多个CSV文件到数据库
python -m tools.video_info_collector --merge movies.csv
python -m tools.video_info_collector --merge tv_shows.csv
python -m tools.video_info_collector --merge documentaries.csv

# 合并到自定义数据库
python -m tools.video_info_collector --merge my_videos.csv --database projects/custom.db
```

**合并功能特性：**
- 🔍 **重复检测**：自动检测并避免重复导入相同文件
- 🛡️ **强制合并**：使用 `--force` 参数可以强制重新导入
- 📊 **进度显示**：显示合并进度和统计信息

### 第四步：视频查询功能

数据导入完成后，可以使用查询功能快速查找特定视频：

```bash
# 通过视频code查询单个视频（文件名去掉后缀）
python -m tools.video_info_collector --search-video-code "ABC-123"

# 查询多个视频code（逗号分隔）
python -m tools.video_info_collector --search-video-code "ABC-123,DEF-456,GHI-789"

# 查询多个视频code（空格分隔）
python -m tools.video_info_collector --search-video-code "ABC-123 DEF-456 GHI-789"

# 从自定义数据库查询
python -m tools.video_info_collector --search-video-code "ABC-123" --database projects/movies.db

# 大小写不敏感查询
python -m tools.video_info_collector --search-video-code "abc-123 DEF-456"
```

**查询功能特性：**
- 🔍 **精确匹配**：基于文件名（去掉扩展名）进行精确查询
- 📋 **简洁输出**：只显示视频code、文件大小、逻辑路径三个关键字段
- 🔤 **大小写不敏感**：自动忽略大小写差异
- 🧹 **自动清理**：自动去除前后空格
- 📊 **多查询支持**：支持同时查询多个视频code

**查询输出示例：**
```
查询结果:
+----------+-----------+---------------------------+
| Code     | File Size | Logical Path              |
+----------+-----------+---------------------------+
| ABC-123  | 5.55G     | /Volumes/WS-2/media/videos|
| DEF-456  | 2.62G     | /Volumes/WS-2/media/videos|
+----------+-----------+---------------------------+
```

### 第五步：数据统计分析

使用统计功能了解视频库的整体情况：

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

# 从自定义数据库进行统计
python -m tools.video_info_collector stats --type basic --database projects/movies.db
```

**统计功能特性：**
- 📊 **多维度统计**：支持基本、标签、分辨率、时长、增强等多种统计类型
- 📈 **美观表格**：使用表格格式清晰展示统计结果
- 🔢 **详细数据**：包含总数、总大小、总时长、平均值等详细信息
- 🏷️ **标签分析**：按标签分组显示视频数量分布
- 📐 **分辨率分析**：按分辨率分组统计视频质量分布
- ⏱️ **时长分析**：按时长范围分组统计视频长度分布

**统计输出示例：**
```bash
# 基本统计输出
基本统计信息:
+----------------+-------+
| 统计项         | 数值  |
+----------------+-------+
| 总视频数       | 1,247 |
| 总文件大小     | 2.5T  |
| 总时长         | 1,234:56:78 |
| 平均文件大小   | 2.1G  |
| 平均时长       | 01:32:15 |
+----------------+-------+

# 按标签统计输出
按标签统计:
+----------+--------+
| 标签     | 数量   |
+----------+--------+
| 电影     | 856    |
| 电视剧   | 234    |
| 纪录片   | 157    |
+----------+--------+
```

### 第六步：数据导出和分析

```bash
# 导出数据库内容为CSV进行分析
python -m tools.video_info_collector --export output/video_info_collector/database/video_database.db --output analysis.csv

# 导出为JSON格式
python -m tools.video_info_collector --export output/video_info_collector/database/video_database.db --output analysis.json --format json

# 简化导出（仅包含文件名、文件大小、逻辑路径）
python -m tools.video_info_collector --export-simple output/video_info_collector/database/video_database.db --output simple_list.txt

# 简化导出到默认路径（自动生成文件名）
python -m tools.video_info_collector --export-simple output/video_info_collector/database/video_database.db

# 从不同数据库导出数据
python -m tools.video_info_collector --export projects/movies.db --output movies_list.csv
python -m tools.video_info_collector --export-simple projects/movies.db --output movies_simple.txt
```

**简化导出功能特性：**
- 📋 **精简格式**：仅包含 filename（去掉后缀）、filesize、logical_path 三个字段
- 📏 **文件大小格式化**：自动转换为GB单位，保留两位小数（如 5.55G）
- 📄 **纯文本输出**：每行格式为 "filename_without_ext filesize logical_path"，用空格分隔
- 🎯 **快速浏览**：适合快速查看文件列表和大小信息

**简化导出输出示例：**
```
DEMO-072 5.55G /Volumes/WS-2/media/videos
TEST-659 2.62G /Volumes/WS-2/media/videos
SAMPLE-015 2.86G /Volumes/WS-2/media/videos
EXAMPLE-730 6.18G /Volumes/WS-2/media/videos
VIDEO-220 2.63G /Volumes/WS-2/media/videos
```

## 完整工作流程示例

```bash
#!/bin/bash

# 1. 初始化数据库
python -m tools.video_info_collector --init-db --database projects/media_library.db

# 2. 分别扫描不同类型的媒体到CSV文件
python -m tools.video_info_collector /media/movies --output temp_movies.csv --tags "电影" --path "媒体库/电影"
python -m tools.video_info_collector /media/tv_shows --output temp_tv.csv --tags "电视剧" --path "媒体库/电视剧"
python -m tools.video_info_collector /media/documentaries --output temp_docs.csv --tags "纪录片" --path "媒体库/纪录片"

# 3. 人工检查CSV文件内容（在此步骤手动检查文件）
echo "请检查生成的CSV文件：temp_movies.csv, temp_tv.csv, temp_docs.csv"
echo "确认无误后按回车继续..."
read

# 4. 合并CSV文件到数据库
python -m tools.video_info_collector --merge temp_movies.csv --database projects/media_library.db
python -m tools.video_info_collector --merge temp_tv.csv --database projects/media_library.db
python -m tools.video_info_collector --merge temp_docs.csv --database projects/media_library.db

# 5. 导出完整列表进行验证
python -m tools.video_info_collector --export projects/media_library.db --output complete_media_list.csv

# 6. 导出简化列表（可选）
python -m tools.video_info_collector --export-simple projects/media_library.db --output simple_media_list.txt

echo "工作流程完成！请检查以下文件："
echo "- complete_media_list.csv (完整信息)"
echo "- simple_media_list.txt (简化列表)"
```

## 主要参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--init-db` | 初始化/重置数据库（清空所有数据） | `--init-db` |
| `--database` | SQLite数据库文件路径 | `--database my_videos.db` |
| `--output` | 输出文件路径 | `--output my_videos.csv` |
| `--merge` | 合并CSV文件到数据库 | `--merge temp_file.csv` |
| `--export` | 从数据库导出到文件 | `--export database.db` |
| `--export-simple` | 简化导出（仅包含filename、filesize、logical_path） | `--export-simple database.db` |
| `--tags` | 为所有文件添加的标签（逗号分隔） | `--tags "电影,高清"` |
| `--path` | 逻辑路径信息 | `--path "媒体库/电影/2024"` |
| `--format` | 导出格式：csv/json | `--format json` |
| `--force` | 强制合并（忽略重复检测） | `--force` |

## 故障排除

### 常见错误

1. **"目录不存在"**：检查路径是否正确
2. **"权限被拒绝"**：确保有读取目录和文件的权限
3. **"无法提取元数据"**：文件可能损坏或格式不支持
4. **"数据库文件损坏"** 或 **"无法打开数据库"**：使用 `--init-db` 重新初始化数据库
5. **"database disk image is malformed"**：数据库结构不兼容，使用 `--init-db` 重置数据库

### 调试技巧

```bash
# 检查数据库表结构
sqlite3 output/video_info_collector/database/video_database.db ".tables"
sqlite3 output/video_info_collector/database/video_database.db ".schema video_info"

# 检查数据库内容
sqlite3 output/video_info_collector/database/video_database.db "SELECT COUNT(*) FROM video_info;"
sqlite3 output/video_info_collector/database/video_database.db "SELECT filename, width, height FROM video_info LIMIT 10;"

# 数据库问题排查和修复
# 如果数据库无法打开或出现错误，重新初始化
python -m tools.video_info_collector --init-db

# 验证数据库文件格式
file output/video_info_collector/database/video_database.db
```

---

## 可选功能（高级用户）

以下功能虽然方便，但存在一定风险，建议谨慎使用：

### 直接扫描到数据库（⚠️ 风险操作）

**警告**：此操作会直接将扫描结果写入数据库，无法预览和修正。一旦参数错误或扫描到错误文件，无法轻易回退。**强烈建议使用上述推荐工作流程**。

```bash
# 直接扫描并存储到数据库（不推荐）
python -m tools.video_info_collector /path/to/videos --output-format sqlite --output videos.db

# 直接扫描到默认数据库（不推荐）
python -m tools.video_info_collector /path/to/videos --database my_videos.db
```

### 其他高级参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--temp-file` | 临时收集文件名 | `--temp-file temp_videos.csv` |
| `--dry-run` | 预览模式，不写入文件 | `--dry-run` |
| `--recursive` | 递归扫描子目录 | `--recursive` |
| `--extensions` | 视频文件扩展名过滤 | `--extensions "mp4,avi,mkv"` |
| `--output-format` | 输出格式：csv/sqlite | `--output-format sqlite` |
| `--duplicate-strategy` | 重复项处理策略 | `--duplicate-strategy update` |

### 处理策略示例

```bash
# 跳过重复文件（默认）
python -m tools.video_info_collector /path/to/videos --duplicate-strategy skip

# 更新重复文件信息
python -m tools.video_info_collector /path/to/videos --duplicate-strategy update

# 追加重复文件（允许重复记录）
python -m tools.video_info_collector /path/to/videos --duplicate-strategy append
```

### 查看帮助信息

```bash
python -m tools.video_info_collector --help
```

## 注意事项

1. **数据库文件**：默认使用 `output/video_info_collector/database/video_database.db`，可以通过 `--database` 参数指定其他文件
2. **扫描性能**：大目录扫描可能需要较长时间，建议分批处理
3. **文件格式**：支持常见的视频格式（mp4, avi, mkv, mov, wmv, flv, webm, m4v）
4. **错误处理**：如果某个文件无法处理，会显示错误信息但继续处理其他文件
5. **安全建议**：始终使用推荐的工作流程，避免直接操作数据库的风险