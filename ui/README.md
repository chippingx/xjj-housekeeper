# UI 模块文档

## 概述

UI模块是XJJ Housekeeper项目的前端界面层，提供基于Streamlit的Web界面和基于tkinter的桌面应用两种部署方式。

## 技术栈

### Web版本（Streamlit）
- **框架**: Streamlit 1.39.0+
- **语言**: Python 3.10+
- **样式**: 自定义HTML/CSS（内联样式）
- **JavaScript**: 原生JS（无外部库）
- **数据库**: SQLite3
- **后端服务**: 基于 `tools/video_info_collector` 模块

### 桌面版本（tkinter）
- **框架**: tkinter (Python内置)
- **语言**: Python 3.10+
- **打包工具**: PyInstaller
- **跨平台**: Windows/macOS/Linux

## 代码结构

```
ui/
├── README.md                 # 本文档
├── app.py                    # 主应用入口（Streamlit版）
├── services.py               # 业务逻辑服务层
├── table_renderer.py         # 表格渲染器
├── validation.py             # 输入验证
├── maintain_form.py          # 维护表单组件
└── design/                   # 设计文档目录
    ├── design_system.md      # 设计系统规范
    └── ...
```

### 文件说明

#### 1. `app.py` - 主应用入口
**职责**: 应用路由、页面渲染、状态管理

**核心功能**:
- 双页面路由系统（查询/维护）
- Session State管理
- 页面组件编排
- 查询交互逻辑

**关键常量**:
```python
ROUTE_QUERY = "query"           # 查询路由
ROUTE_MAINTAIN = "maintain"     # 维护路由
QUERY_PLACEHOLDER = "按视频编号精确查询（示例：ABC-123）"
```

**主要函数**:
- `render_query_page()` - 渲染查询页面
- `render_maintain_page()` - 渲染维护页面
- `_init_session_state()` - 初始化会话状态

#### 2. `services.py` - 业务逻辑服务层
**职责**: 数据库操作、视频扫描、业务逻辑封装

**核心类**:
```python
class VideoService:
    - search_videos(keyword: str) -> List[Dict]
    - start_maintain(path: str, labels: str, logical_path: str) -> Dict
```

**主要功能**:
- 视频搜索（模糊匹配）
- 目录扫描与导入
- 文件大小格式化（GB/MB显示）
- 错误处理与友好提示

**数据库路径**: `output/video_info_collector/database/video_database.db`

#### 3. `table_renderer.py` - 表格渲染器
**职责**: 搜索结果的HTML表格渲染

**功能特点**:
- 自定义HTML表格样式
- 字段映射（数据库字段 → 显示字段）
- 响应式设计（移动端适配）

**字段映射**:
```python
'filename' -> '视频'
'file_size' -> '大小'
'file_path' -> '路径'
'duration' -> 时长（在视频列显示）
'resolution' -> 分辨率（在视频列显示）
```

#### 4. `validation.py` - 输入验证
**职责**: 查询输入的验证逻辑

**验证规则**:
- 禁止空输入
- 禁止通配符（`*`, `?`）
- 支持标准视频编号格式（`ABC-123`）
- 支持通用关键词（至少2个字符）

**正则表达式**:
```python
VIDEO_CODE_REGEX = r"^[A-Z]{3,6}-\d{3,4}$"
```

#### 5. `maintain_form.py` - 维护表单组件
**职责**: 维护页面的表单UI和交互逻辑

**主要功能**:
- 目录选择对话框（跨平台）
- 表单样式定义
- 处理中遮罩
- 完成弹框

**复杂度**: 包含大量JavaScript代码处理浏览器兼容性

## 实现功能

### 1. 查询模式
- ✅ 关键词搜索（文件名、路径）
- ✅ 实时搜索（回车触发）
- ✅ 结果表格显示
- ✅ 文件大小格式化
- ✅ 空态提示

### 2. 维护模式
- ✅ 目录选择（文件对话框）
- ✅ 视频扫描导入
- ✅ 进度反馈
- ✅ 错误提示
- ✅ 完成弹框

### 3. 交互优化
- ✅ 回车键查询
- ✅ 按钮状态管理
- ✅ Session State持久化
- ✅ URL路由参数

## 关键技术点

### 1. macOS tkinter线程问题解决方案
**问题**: macOS上tkinter的文件对话框会导致Streamlit崩溃

**解决方案**: 使用subprocess隔离tkinter进程
```python
# 在独立进程中运行tkinter
script_content = '''
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
folder = filedialog.askdirectory(title="选择扫描目录")
root.destroy()

with open(temp_file, "w") as f:
    f.write(folder if folder else "")
'''

subprocess.run([sys.executable, '-c', script_content], ...)
```

**相关文件**: `app.py` 第170-220行

### 2. 搜索交互优化
**问题**: 用户需要回车两次才能触发搜索

**解决方案**: 通过Session State追踪输入变化
```python
if "previous_query" not in st.session_state:
    st.session_state.previous_query = ""

current_query = query.strip()
if current_query != st.session_state.previous_query:
    if current_query:  # 只有非空内容才触发查询
        do_search = True
    st.session_state.previous_query = current_query
```

**相关文件**: `app.py` 第79-87行

### 3. 字段映射问题
**问题**: 数据库返回字段与表格显示字段不匹配

**解决方案**: 在`table_renderer.py`中添加映射层
```python
def render_search_results_table(rows: List[Dict[str, str]]) -> str:
    mapped_rows = []
    for row in rows:
        mapped_row = {
            '视频': f"{row.get('filename', '')}<br><small>{row.get('duration', '')} | {row.get('resolution', '')}</small>",
            '大小': row.get('file_size', ''),
            '路径': row.get('file_path', '')
        }
        mapped_rows.append(mapped_row)
    return render_table(mapped_rows)
```

**相关文件**: `table_renderer.py` 第23-34行

### 4. 文件大小格式化
**需求**: 显示为两位小数的GB单位

**实现**:
```python
file_size_gb = file_size_bytes / (1024 * 1024 * 1024)
if file_size_gb >= 1:
    file_size_formatted = f"{file_size_gb:.2f}G"
else:
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_size_formatted = f"{file_size_mb:.0f}M"
```

**相关文件**: `services.py` 第75-82行

## 已知问题与解决方案

### 1. ❌ 文件对话框在macOS崩溃
**状态**: ✅ 已解决

**解决方案**: 使用subprocess隔离tkinter进程

**影响范围**: 维护页面的"选择目录"功能

### 2. ❌ 搜索需要回车两次
**状态**: ✅ 已解决

**解决方案**: Session State追踪输入变化，自动触发搜索

**影响范围**: 查询页面的搜索交互

### 3. ❌ 搜索结果表格显示空白
**状态**: ✅ 已解决

**解决方案**: 添加字段映射层，统一数据格式

**影响范围**: 查询结果显示

### 4. ❌ 数据导入后显示误导性警告
**状态**: ✅ 已解决

**解决方案**: 区分"无文件"和"处理失败"两种情况，提供详细统计信息

**影响范围**: 维护页面的错误提示

### 5. ⚠️ 浏览器兼容性问题
**状态**: 部分解决

**问题**: File System Access API仅在Chrome 86+和Edge 86+中支持

**解决方案**: 提供降级方案（手动输入路径）+ 友好提示

**影响范围**: 维护页面的目录选择功能

**改进建议**: 考虑使用传统的`<input type="file" webkitdirectory>`作为降级方案

## 独立客户端部署

### Web版（Streamlit）
**启动方式**:
```bash
# 使用poetry
poetry run streamlit run ui/app.py

# 使用启动脚本
./start-xjj-housekeeper.sh
python xjj_housekeeper_client.py
```

**特点**:
- 基于浏览器
- 热重载开发
- 跨平台访问

### 桌面版（tkinter）
**启动方式**:
```bash
# 开发模式
poetry run python xjj_housekeeper_desktop_full.py

# 打包模式
python build_desktop_app.py
./dist/XJJ-Housekeeper
```

**特点**:
- 独立窗口应用
- 无需浏览器
- 原生系统集成
- 可打包为单文件

**相关文件**:
- `../xjj_housekeeper_desktop_full.py` - 完整桌面应用
- `../build_desktop_app.py` - 打包脚本
- `../run-desktop.sh` - Unix启动脚本
- `../run-desktop.bat` - Windows启动脚本

## 后续改进点

### 功能增强
1. **高级搜索**
   - [ ] 多条件组合搜索
   - [ ] 正则表达式搜索
   - [ ] 搜索历史记录
   - [ ] 搜索结果导出

2. **批量操作**
   - [ ] 批量删除
   - [ ] 批量编辑元数据
   - [ ] 批量导出

3. **数据可视化**
   - [ ] 视频数量统计图表
   - [ ] 存储空间分布
   - [ ] 时长分布分析

4. **文件预览**
   - [ ] 视频缩略图
   - [ ] 视频播放器集成
   - [ ] 元数据详情页

### 技术优化
1. **性能优化**
   - [ ] 搜索结果分页
   - [ ] 虚拟滚动（大量结果）
   - [ ] 数据库查询优化
   - [ ] 缓存机制

2. **用户体验**
   - [ ] 深色模式
   - [ ] 快捷键支持
   - [ ] 拖拽文件导入
   - [ ] 更好的加载状态

3. **浏览器兼容性**
   - [ ] Safari支持优化
   - [ ] Firefox兼容性测试
   - [ ] 移动端适配

4. **错误处理**
   - [ ] 更详细的错误提示
   - [ ] 错误日志收集
   - [ ] 崩溃恢复机制

### 代码质量
1. **重构**
   - [ ] 拆分大文件（`maintain_form.py`过大）
   - [ ] 提取JavaScript到独立文件
   - [ ] 组件化改造

2. **测试**
   - [ ] 单元测试覆盖
   - [ ] 集成测试
   - [ ] UI自动化测试

3. **文档**
   - [ ] API文档
   - [ ] 组件使用示例
   - [ ] 贡献指南

## 注意事项

### 开发环境
1. **Python版本**: 必须 >= 3.10
2. **依赖管理**: 使用poetry，不要混用pip
3. **数据库路径**: 确保 `output/video_info_collector/database/` 目录存在

### Streamlit特性
1. **状态管理**: 使用 `st.session_state` 而非全局变量
2. **重运行机制**: 每次交互都会重新运行整个脚本
3. **缓存**: 使用 `@st.cache_data` 缓存昂贵计算

### 浏览器要求
1. **推荐浏览器**: Chrome 86+, Edge 86+
2. **不推荐**: Safari (File System Access API支持有限)
3. **移动端**: 仅基本功能可用

### macOS特殊问题
1. **tkinter**: 必须使用subprocess隔离
2. **文件权限**: 首次运行可能需要授权文件访问
3. **安全设置**: 打包应用可能需要开发者签名

## 设计规范

详见 `design/design_system.md`，包括：
- 颜色系统
- 排版规范
- 组件样式
- 交互规范

## 相关文档

- [项目主README](../README.md)
- [桌面应用文档](../README_DESKTOP.md)
- [客户端部署文档](../README_CLIENT.md)
- [开发指南](../DEVELOPMENT_GUIDELINES.md)
- [术语表](../TERMINOLOGY.md)

## 维护者

如有问题或建议，请参考项目主README中的联系方式。

---

**最后更新**: 2025-11-06  
**版本**: 0.1.0  
**状态**: 开发中