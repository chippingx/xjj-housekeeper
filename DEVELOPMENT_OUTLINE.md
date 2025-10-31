# 开发纲要 (Development Outline)

## 项目概述

**xjj_housekeeper** 是一个面向本地下载视频文件的整理工具集合，旨在提供高效、安全的视频文件管理解决方案。

### 核心目标
- 提供文件名规范化工具，清理和标准化视频文件名
- 提供视频元数据收集工具，建立视频文件清单
- 确保操作安全性，绝不覆盖现有文件
- 支持批量处理和自动化工作流

## 技术栈

### 编程语言与版本
- **Python 3.10+**：主要开发语言
- 兼容性：支持 Python 3.10、3.11、3.12

### 依赖管理
- **Poetry**：主要包管理工具
- **pyproject.toml**：项目配置和依赖声明

### 核心依赖

#### Python 包依赖
- **pyyaml** (^6.0.2)：YAML 配置文件解析
- **python-dotenv** (^1.0.0)：环境变量管理

#### 开发依赖
- **pytest** (^7.4.3)：测试框架
- **pytest-cov** (^4.1.0)：测试覆盖率
- **pytest-mock** (^3.12.0)：模拟测试
- **pytest-xdist** (^3.5.0)：并行测试

#### 系统依赖
- **FFmpeg** (包含 ffprobe)：视频元数据提取
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: 下载并安装 FFmpeg 二进制文件
- **SQLite3**：数据库支持（通常系统自带）

## 架构设计

### 项目结构
```
xjj_housekeeper/
├── tools/                          # 工具集合
│   ├── filename_formatter/          # 文件名规范化工具
│   │   ├── formatter.py            # 核心逻辑
│   │   ├── cli.py                  # 命令行接口
│   │   ├── rollback.py             # 回滚功能
│   │   ├── rename_rules.yaml       # 默认规则配置
│   │   └── README.md               # 工具文档
│   └── video_info_collector/        # 视频信息收集工具
│       ├── scanner.py              # 文件扫描器
│       ├── metadata.py             # 元数据提取器
│       ├── csv_writer.py           # CSV 导出
│       ├── sqlite_storage.py       # SQLite 存储
│       ├── cli.py                  # 命令行接口
│       ├── config.yaml             # 配置文件
│       └── README.md               # 工具文档
├── tests/                          # 测试套件
│   ├── tool_filename_formatter/    # 文件名工具测试
│   │   ├── test_data/              # 测试数据
│   │   └── *.py                    # 测试文件
│   └── tool_video_info_collector/  # 视频信息工具测试
├── pyproject.toml                  # 项目配置
├── README.md                       # 项目说明
├── HANDOVER.md                     # 交接文档
└── DEVELOPMENT_OUTLINE.md          # 开发纲要（本文件）
```

### 设计原则

#### 1. 安全第一
- 绝不覆盖现有文件
- 提供预览模式（dry-run）
- 支持操作日志和回滚
- 文件大小验证

#### 2. 配置驱动
- YAML 配置文件
- 环境变量覆盖
- 命令行参数优先级
- 灵活的规则系统

#### 3. 模块化设计
- 独立的工具模块
- 清晰的接口定义
- 可扩展的架构
- 单一职责原则

#### 4. 测试覆盖
- 单元测试
- 集成测试
- 回归测试
- 性能测试

## 核心功能

### 1. 文件名规范化工具 (filename_formatter)

#### 功能特性
- **规则驱动**：基于 YAML 配置的字符串替换规则
- **格式标准化**：将文件名转换为 `ABC-123.mp4` 格式
- **扁平化输出**：默认将子目录文件移动到根目录
- **冲突处理**：支持跳过或自动重命名策略
- **批量处理**：递归处理目录结构
- **安全保障**：预览模式、操作日志、文件验证

#### 核心算法
```python
# 格式化策略
def format_filename(filename: str) -> str:
    # 1. 提取字母和数字部分
    # 2. 字母部分转大写
    # 3. 添加连字符分隔
    # 4. 保留原扩展名
    # 模式：ABC-123.mp4
```

#### 配置优先级
1. 构造函数参数
2. 环境变量
3. YAML 配置文件
4. 默认值

### 2. 视频信息收集工具 (video_info_collector)

#### 功能特性
- **元数据提取**：使用 FFmpeg 提取视频信息
- **多格式支持**：支持 mp4、mkv、avi、mov 等格式
- **数据存储**：SQLite 数据库和 CSV 文件
- **批量扫描**：递归目录扫描
- **标签管理**：支持自定义标签系统

#### 数据模型
```python
class VideoInfo:
    file_path: str
    filename: str
    width: int
    height: int
    duration: float
    video_codec: str
    audio_codec: str
    file_size: int
    bit_rate: int
    frame_rate: float
    created_time: datetime
```

## 开发工作流

### 环境设置
```bash
# 1. 克隆项目
git clone <repository>
cd xjj_housekeeper

# 2. 安装系统依赖
brew install ffmpeg  # macOS

# 3. 安装 Python 依赖
poetry install --with dev,test

# 4. 运行测试
poetry run pytest -v
```

### 代码规范

#### 文件组织
- 每个工具独立目录
- 清晰的模块分离
- 统一的命名约定
- 完整的文档注释

#### 测试策略
- 单元测试：测试核心逻辑
- 集成测试：测试完整工作流
- 回归测试：基于真实数据
- 性能测试：大规模文件处理

#### 配置管理
- YAML 格式配置文件
- 环境变量支持
- 配置验证和默认值
- 向后兼容性

### 发布流程

#### 版本管理
- 语义化版本控制 (SemVer)
- 变更日志维护
- 标签和发布说明

#### 质量保证
- 自动化测试
- 代码覆盖率检查
- 静态代码分析
- 文档更新

## 扩展路线

### 短期目标 (v0.2.0)
- [ ] 增强规则系统（正则表达式支持）
- [ ] 改进 CLI 用户体验
- [ ] 添加更多测试用例
- [ ] 性能优化

### 中期目标 (v0.3.0)
- [ ] GUI 界面开发
- [ ] 跨平台打包
- [ ] 插件系统
- [ ] 配置向导

### 长期目标 (v1.0.0)
- [ ] 云存储集成
- [ ] 机器学习文件分类
- [ ] 多语言支持
- [ ] 企业级功能

## 依赖维护策略

### 定期更新
- 每月检查依赖更新
- 安全补丁及时应用
- 兼容性测试
- 文档同步更新

### 依赖监控
- 使用 Poetry 管理版本
- 监控安全漏洞
- 评估新依赖引入
- 清理无用依赖

### 系统依赖
- FFmpeg 版本兼容性
- Python 版本支持
- 操作系统适配
- 性能基准测试

## 贡献指南

### 开发环境
1. Fork 项目仓库
2. 创建功能分支
3. 安装开发依赖
4. 运行测试套件
5. 提交 Pull Request

### 代码提交
- 清晰的提交信息
- 单一功能提交
- 测试覆盖新功能
- 文档更新同步

### 问题报告
- 使用 Issue 模板
- 提供复现步骤
- 包含环境信息
- 附加相关日志

---

**最后更新**: 2024年1月
**维护者**: 项目团队
**版本**: v0.1.0