# TERMINOLOGY - 项目术语表

> ⚠️ **安全检查范围说明**: 本文档中的示例数据（如 `ABC-123`、`DEF-456`）仅用于说明格式规范。
> 根据项目安全策略，只有**纳入版本控制**的文件需要进行敏感信息脱敏，`.gitignore` 中排除的文件（如 `output/` 目录）可以包含真实数据。

## 📋 目录
- [核心概念定义](#核心概念定义)
- [数据库字段规范](#数据库字段规范)
- [变量命名规范](#变量命名规范)
- [API接口规范](#api接口规范)
- [CLI参数规范](#cli参数规范)
- [文件命名规范](#文件命名规范)
- [术语一致性检查](#术语一致性检查)

---

## 🎯 核心概念定义

### 1. Video Code (视频编码)
**标准术语**: `video_code`
**定义**: 从视频文件名中提取的业务标识符，用于唯一标识视频内容
**格式**: 通常为字母-数字组合，如 `ABC-123`、`DEF-456`
**用途**: 防重复下载、内容管理、查询检索

**命名规范**:
- ✅ **数据库字段**: `video_code`
- ✅ **Python变量**: `video_code`
- ✅ **CLI参数**: `--search-video-code`
- ✅ **API方法**: `search_videos_by_video_codes()`
- ❌ **禁用**: `code`, `search_code`, `video_id`, `vid_code`

### 2. File Fingerprint (文件指纹)
**标准术语**: `file_fingerprint`
**定义**: 基于文件元数据生成的轻量级唯一标识符
**组成**: filename + file_size + video_code 的哈希值
**用途**: 文件移动检测、重复文件识别

### 3. File Status (文件状态)
**标准术语**: `file_status`
**定义**: 文件在系统中的当前状态
**可选值**: `present`, `missing`, `deleted`
**用途**: 文件生命周期管理、清理策略

---

## 🗄️ 数据库字段规范

### 主表 (video_info)
| 字段名 | 数据类型 | 说明 | 必填 |
|--------|----------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 | ✅ |
| `file_path` | TEXT UNIQUE NOT NULL | 文件完整路径 | ✅ |
| `filename` | TEXT NOT NULL | 文件名（含扩展名） | ✅ |
| `width` | INTEGER | 视频宽度（像素） | ❌ |
| `height` | INTEGER | 视频高度（像素） | ❌ |
| `resolution` | TEXT | 分辨率字符串（如"1920x1080"） | ❌ |
| `duration` | REAL | 视频时长（秒） | ❌ |
| `duration_formatted` | TEXT | 格式化时长（HH:MM:SS） | ❌ |
| `video_codec` | TEXT | 视频编码格式 | ❌ |
| `audio_codec` | TEXT | 音频编码格式 | ❌ |
| `file_size` | INTEGER | 文件大小（字节） | ❌ |
| `bit_rate` | INTEGER | 比特率 | ❌ |
| `frame_rate` | REAL | 帧率 | ❌ |
| `logical_path` | TEXT | 逻辑路径 | ❌ |
| `created_time` | TEXT NOT NULL | 文件创建时间 | ✅ |
| `updated_time` | TEXT | 记录更新时间 | ❌ |
| `video_code` | TEXT | 视频编码标识符 | ❌ |
| `file_fingerprint` | TEXT | 文件指纹 | ❌ |
| `file_status` | TEXT DEFAULT 'present' | 文件状态 | ✅ |
| `last_scan_time` | TEXT | 最后扫描时间 | ❌ |
| `last_merge_time` | TEXT | 最后合并时间 | ❌ |

### 标签表 (video_tags)
| 字段名 | 数据类型 | 说明 | 必填 |
|--------|----------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 | ✅ |
| `video_id` | INTEGER NOT NULL | 关联video_info.id | ✅ |
| `tag` | TEXT NOT NULL | 标签内容 | ✅ |
| `created_time` | TIMESTAMP | 标签创建时间 | ✅ |

### 扫描历史表 (scan_history)
| 字段名 | 数据类型 | 说明 | 必填 |
|--------|----------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 | ✅ |
| `scan_path` | TEXT NOT NULL | 扫描路径 | ✅ |
| `scan_time` | TEXT | 扫描时间 | ✅ |
| `files_found` | INTEGER | 发现文件数 | ❌ |
| `files_processed` | INTEGER | 处理文件数 | ❌ |
| `tags` | TEXT | 扫描标签 | ❌ |
| `logical_path` | TEXT | 逻辑路径 | ❌ |
| `status` | TEXT | 扫描状态 | ❌ |

### 主列表表 (video_master_list)
| 字段名 | 数据类型 | 说明 | 必填 |
|--------|----------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 | ✅ |
| `video_code` | TEXT UNIQUE NOT NULL | 视频编码 | ✅ |
| `file_fingerprint` | TEXT | 文件指纹 | ❌ |
| `status` | TEXT DEFAULT 'active' | 状态 | ✅ |
| `file_count` | INTEGER DEFAULT 1 | 文件数量 | ❌ |
| `first_seen` | TEXT | 首次发现时间 | ❌ |
| `last_updated` | TEXT | 最后更新时间 | ❌ |
| `notes` | TEXT | 备注 | ❌ |

### 合并历史表 (merge_history)
| 字段名 | 数据类型 | 说明 | 必填 |
|--------|----------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 | ✅ |
| `merge_time` | TEXT | 合并时间 | ✅ |
| `event_type` | TEXT NOT NULL | 事件类型 | ✅ |
| `video_code` | TEXT | 视频编码 | ❌ |
| `old_path` | TEXT | 旧路径 | ❌ |
| `new_path` | TEXT | 新路径 | ❌ |
| `details` | TEXT | 详细信息 | ❌ |
| `scan_session_id` | TEXT | 扫描会话ID | ❌ |

---

## 🐍 变量命名规范

### Python类属性
```python
class VideoInfo:
    # ✅ 正确命名
    self.video_code: Optional[str] = None
    self.file_fingerprint: Optional[str] = None
    self.file_status: str = 'present'
    self.last_merge_time: Optional[datetime] = None
    
    # ❌ 禁用命名
    self.code  # 太模糊
    self.vid_code  # 非标准缩写
    self.video_id  # 与数据库主键混淆
```

### 函数参数命名
```python
# ✅ 正确命名
def search_videos_by_video_codes(self, video_codes: List[str]) -> List[Dict[str, Any]]:
def extract_video_code(self, filename: str) -> Optional[str]:
def update_file_status(self, file_path: str, status: str) -> bool:

# ❌ 禁用命名
def search_videos_by_codes(self, codes: List[str]):  # 缺少video前缀
def search_by_code(self, code: str):  # 太模糊
```

### 局部变量命名
```python
# ✅ 正确命名
video_codes = [v['video_code'] for v in videos]
file_fingerprint = self._generate_fingerprint()
current_file_status = video_info.file_status

# ❌ 禁用命名
codes = [v['code'] for v in videos]  # 太模糊
fingerprint = self._generate_fingerprint()  # 缺少file前缀
status = video_info.status  # 太模糊
```

---

## 🔌 API接口规范

### SQLiteStorage类方法
```python
# ✅ 标准方法名
def search_videos_by_video_codes(self, video_codes: List[str]) -> List[Dict[str, Any]]:
def update_video_code(self, video_id: int, video_code: str) -> bool:
def get_videos_by_file_status(self, status: str) -> List[VideoInfo]:
def update_file_fingerprint(self, video_id: int, fingerprint: str) -> bool:

# ❌ 禁用方法名
def search_videos_by_codes(self, codes: List[str]):  # 缺少video前缀
def search_by_code(self, code: str):  # 太模糊
def get_videos_by_status(self, status: str):  # 缺少file前缀
```

### 返回值字段名
```python
# ✅ 正确返回格式
{
    'video_code': 'ABC-123',
    'file_size': 1024000,
    'logical_path': '/movies/action',
    'filename': 'ABC-123.mp4',
    'file_status': 'present',
    'file_fingerprint': 'abc123def456'
}

# ❌ 禁用返回格式
{
    'code': 'ABC-123',  # 缺少video前缀
    'size': 1024000,  # 缺少file前缀
    'status': 'present',  # 太模糊
    'fingerprint': 'abc123def456'  # 缺少file前缀
}
```

---

## 💻 CLI参数规范

### 命令行参数
```bash
# ✅ 正确参数名
--search-video-code ABC-123,DEF-456
--update-file-status present
--export-video-codes
--filter-by-file-status missing

# ❌ 禁用参数名
--search-code ABC-123  # 缺少video前缀
--search-codes ABC-123  # 复数形式不一致
--update-status present  # 缺少file前缀
--export-codes  # 缺少video前缀
```

### 参数dest属性
```python
# ✅ 正确dest命名
parser.add_argument('--search-video-code', dest='search_video_codes')
parser.add_argument('--update-file-status', dest='update_file_status')

# ❌ 禁用dest命名
parser.add_argument('--search-video-code', dest='search_codes')  # 不一致
parser.add_argument('--update-file-status', dest='update_status')  # 缺少前缀
```

---

## 📁 文件命名规范

### 模块文件名
```
# ✅ 正确文件名
video_code_extractor.py  # 视频编码提取器
file_status_manager.py   # 文件状态管理器
sqlite_storage.py        # SQLite存储模块

# ❌ 禁用文件名
code_extractor.py        # 缺少video前缀
status_manager.py        # 缺少file前缀
storage.py               # 太模糊
```

### 测试文件名
```
# ✅ 正确测试文件名
test_video_code_extraction.py
test_file_status_system.py
test_sqlite_storage.py

# ❌ 禁用测试文件名
test_code_extraction.py     # 缺少video前缀
test_status_system.py       # 缺少file前缀
test_storage.py             # 太模糊
```

---

## ✅ 术语一致性检查

### 检查清单

#### 数据库层面
- [ ] 所有表中的video_code字段命名一致
- [ ] file_status字段在所有相关表中保持一致
- [ ] file_fingerprint字段命名标准化
- [ ] 外键关系使用标准字段名

#### 代码层面
- [ ] VideoInfo类属性使用标准命名
- [ ] SQLiteStorage方法名遵循规范
- [ ] 函数参数名保持一致性
- [ ] 返回值字典键名标准化

#### CLI层面
- [ ] 命令行参数使用连字符分隔
- [ ] 参数dest属性与变量名一致
- [ ] 帮助文档使用标准术语
- [ ] 错误信息使用规范术语

#### 测试层面
- [ ] 测试用例使用标准字段名
- [ ] Mock数据结构符合规范
- [ ] 断言检查使用正确术语
- [ ] 测试文件名遵循命名规范

#### 文档层面
- [ ] README使用标准术语
- [ ] API文档字段名一致
- [ ] 示例代码遵循规范
- [ ] 注释使用规范术语

### 违规检测命令
```bash
# 检测非标准video_code使用
grep -r "search_code\|vid_code\|video_id.*code" --include="*.py" .

# 检测非标准file_status使用
grep -r "\.status\|file\.status" --include="*.py" .

# 检测非标准方法名
grep -r "search.*by.*code[^s]" --include="*.py" .

# 检测CLI参数不一致
grep -r "search-code\|--code" --include="*.py" .
```

---

## 🔄 术语维护流程

### 1. 新增术语
1. 在本文档中定义新术语
2. 更新相关代码实现
3. 修改测试用例
4. 更新文档说明
5. 运行一致性检查

### 2. 修改术语
1. 评估影响范围
2. 更新术语表定义
3. 系统性修改所有相关代码
4. 更新测试和文档
5. 验证功能完整性

### 3. 废弃术语
1. 标记为废弃状态
2. 提供迁移指南
3. 逐步清理旧用法
4. 从术语表中移除
5. 更新检查脚本

---

## 📚 参考资源

### 相关文档
- [开发规范](DEVELOPMENT_GUIDELINES.md)
- [项目README](README.md)
- [API文档](tools/video_info_collector/README.md)

### 检查工具
- 正则表达式扫描脚本
- 数据库结构验证
- 代码静态分析
- 测试覆盖率检查

---

**最后更新**: 2024-01-20
**维护责任**: 项目开发团队
**审查周期**: 每次重大功能更新后
