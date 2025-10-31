# xjj_housekeeper

面向“本地下载视频文件”的整理工具集合。当前已提供文件名规范化工具（filename_formatter），后续将增加“视频文件清单收集”与可视化界面。

## 工具索引

- **文件名规范化**（tools/filename_formatter）
  - 说明与配置详见：tools/filename_formatter/README.md
  - 支持按规则清理前缀/后缀并格式化为标准名称
  - 按配置处理扩展名（默认 .mp4/.mkv/.mov）与最小文件大小（默认 100MB）

- **视频信息收集**（tools/video_info_collector）
  - 说明与配置详见：tools/video_info_collector/README.md
  - 使用 FFmpeg 提取视频元数据（分辨率、时长、编码等）
  - 支持 CSV/JSON 导出和 SQLite 数据库存储

## 快速开始

### 1) 环境要求
- Python 3.10+
- 系统依赖：
  - **FFmpeg** (包含 ffprobe)：用于视频元数据提取
    - macOS: `brew install ffmpeg`
    - Ubuntu/Debian: `sudo apt-get install ffmpeg`
    - Windows: 下载并安装 FFmpeg 二进制文件
  - **SQLite3**: 通常系统自带，Python 内置支持

### 2) 安装依赖
推荐使用 Poetry 管理依赖：

**基础安装**：
```bash
poetry install
```

**开发环境**（包含测试工具）：
```bash
poetry install --with dev,test
```

**或使用 pip**：
```bash
# 运行依赖
pip install pyyaml python-dotenv

# 开发依赖（可选）
pip install pytest pytest-cov pytest-mock pytest-xdist
```

### 3) 运行工具

**文件名规范化工具**（递归处理子目录）：
```bash
python -m tools.filename_formatter <目录路径>
```

**视频信息收集工具**：
```bash
python -m tools.video_info_collector scan <目录路径>
```

示例输出（节选）：
```
处理目录: /path/to/videos
处理扩展名: .mp4, .mkv, .mov
最小文件大小: 104857600 字节
使用规则文件: tools/filename_formatter/rename_rules.yaml
递归子目录: 是
success: /path/to/videos/sub/ABC123.mp4 -> /path/to/videos/ABC-123.mp4
success: /path/to/videos/sub2/DEF456ch.mp4 -> /path/to/videos/DEF-456.mp4
...
```

## 配置与环境变量

- 配置文件：tools/filename_formatter/rename_rules.yaml
  - settings.video_extensions：处理的扩展名列表（默认 [".mp4", ".mkv", ".mov"]）
  - settings.min_file_size_bytes：最小文件大小阈值（字节，默认 100MB）
  - rename_rules：字符串替换规则（用于清理站点前缀/后缀等）
- 环境变量：
  - RENAME_RULES_PATH：指定规则/配置 YAML 的路径（绝对路径或相对项目根）
  - MIN_VIDEO_SIZE_BYTES：覆盖最小文件大小阈值（字节）

优先级详情与完整示例请查看 tools/filename_formatter/README.md。

## 测试

运行全部单元测试：
```bash
pytest -q
```

运行测试并生成覆盖率报告：
```bash
pytest --cov=tools --cov-report=html
```

运行并行测试（加速）：
```bash
pytest -n auto
```

## 路线图

- 新增“视频文件清单收集”工具：扫描目录并输出名称、大小、格式信息与时间戳等
- 增强文档与示例
- 提供跨平台 GUI（Windows/macOS）

如需功能调整（扩展名范围、阈值、规则文件位置等），请优先修改 YAML 配置或设置环境变量。欢迎提出改进建议或新需求。