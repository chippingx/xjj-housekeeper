# 文件名规范化工具（filename_formatter）

批量规范化/重命名视频文件名，**默认扁平化输出到根目录**。支持按配置文件中的扩展名与最小文件大小进行处理，并应用规则清理前缀/后缀后再格式化为标准形式（示例：ABC-123.mp4）。

## 🎯 功能概览
- **默认扁平化输出** - 自动将所有子目录文件移动到根目录
- **规则驱动的批量重命名** - 安全重命名，不覆盖已存在目标文件
- **智能冲突处理** - 支持跳过或自动重命名冲突文件
- **递归扫描子目录** - 自动处理所有子目录中的文件
- **跳过隐藏文件** - 自动跳过以"."开头的隐藏文件
- **扩展名过滤** - 按配置处理扩展名，默认支持 .mp4/.mkv/.mov
- **文件大小阈值** - 可配置最小文件大小（默认 100MB）
- **预览模式** - 干运行查看将要执行的操作
- **操作日志** - 可选记录所有操作便于回滚
- **文件验证** - 轻量级文件大小验证

## 配置与优先级

工具会从 YAML 配置中读取设置与重命名规则，同时支持环境变量覆盖部分行为。

- 规则文件路径优先级：
  1) 环境变量 RENAME_RULES_PATH（若设置且为绝对路径则直接使用；为相对路径则以项目根拼接）
  2) 代码中传入的 default_rules_path（CLI 默认不强制传入；工具内部会回退到默认）
  3) 默认路径 tools/filename_formatter/rename_rules.yaml

- 最小文件大小（字节）优先级：
  1) 显式传入的构造参数 min_file_size（CLI 不传）
  2) 环境变量 MIN_VIDEO_SIZE_BYTES
  3) 配置文件 settings.min_file_size_bytes
  4) 默认 104857600（100MB）

- 处理的扩展名优先级：
  1) 显式传入的构造参数 video_extensions（CLI 不传）
  2) 配置文件 settings.video_extensions
  3) 默认 [".mp4", ".mkv", ".mov"]

### YAML 配置示例（recommend）
文件：tools/filename_formatter/rename_rules.yaml

```yaml
settings:
  video_extensions: [".mp4", ".mkv", ".mov"]
  min_file_size_bytes: 104857600  # 100MB

rename_rules:
  - pattern: "site1234.com@"
    replace: ""
  - pattern: "ch.mp4"
    replace: ".mp4"
  # ... 其他站点前缀/后缀清理规则
```

说明：
- settings.video_extensions：被处理的视频扩展名列表。添加/移除扩展只需修改此列表。
- settings.min_file_size_bytes：小于该大小的文件将被跳过（用于排除无效/缩略文件）。
- rename_rules：在规范化前先执行字符串替换清理。

## 📋 CLI 用法

### 基本用法
```bash
# 基本用法（默认扁平化输出到根目录）
python -m tools.filename_formatter <目录路径>

# 预览模式：查看将要执行的操作
python -m tools.filename_formatter <目录路径> --dry-run

# 冲突自动重命名：遇到同名文件时自动添加序号
python -m tools.filename_formatter <目录路径> --conflict-resolution rename

# 记录操作日志：便于后续回滚
python -m tools.filename_formatter <目录路径> --log-operations

# 文件大小验证：轻量级验证
python -m tools.filename_formatter <目录路径> --verify-size

# 完整功能组合
python -m tools.filename_formatter <目录路径> --conflict-resolution rename --log-operations --verify-size --dry-run
```

### 可用参数
- `--dry-run` - 预览模式：显示将要执行的操作，但不实际修改文件
- `--conflict-resolution {skip,rename}` - 同名文件冲突处理方式（默认：skip）
- `--log-operations` - 记录所有操作到轻量级日志文件
- `--verify-size` - 验证文件大小（轻量级验证）
- `--version` - 显示版本信息

### 示例输出
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
would skip: target exists: /path/to/videos/sub/ABC-123.mp4 -> /path/to/videos/ABC-123.mp4

统计:
- 总计: 4
- 成功: 2
- 跳过(目标已存在): 1
- 跳过(同名): 1
- 失败: 0
```

### 环境变量配置
- `RENAME_RULES_PATH` - 指定规则/配置 YAML 文件路径（绝对或相对项目根）
- `MIN_VIDEO_SIZE_BYTES` - 覆盖最小文件大小阈值（字节）

## 🔧 行为细节

### 核心行为
1. **默认扁平化** - 所有子目录文件自动移动到根目录，简化文件结构
2. **文件过滤** - 只处理配置中指定的扩展名且大小超过阈值的文件
3. **隐藏文件跳过** - 自动跳过以"."开头的隐藏文件
4. **安全重命名** - 绝不覆盖已存在的目标文件，确保数据安全
5. **递归处理** - 自动扫描所有子目录，无需手动指定
6. **规则应用** - 按 rename_rules.yaml 中的规则清理文件名
7. **格式化** - 应用标准格式（如 ABC-123.mp4）

### 冲突处理策略
- **skip（默认）** - 跳过同名文件，保持原有文件不变
- **rename** - 自动添加序号重命名（如 file_1.mp4, file_2.mp4）

### 安全保障
- ✅ 绝不覆盖现有文件
- ✅ 预览模式可安全查看操作
- ✅ 操作日志支持回滚
- ✅ 文件大小验证确保完整性

## ❓ 常见问题

### 文件处理相关
**Q: 为什么某些文件被跳过？**
A: 可能原因：
- 文件大小小于配置的最小阈值（默认 100MB）
- 扩展名不在配置的处理列表中
- 目标文件名已存在（安全保护）
- 文件是隐藏文件（以"."开头）

**Q: 如何修改处理的扩展名？**
A: 编辑 `rename_rules.yaml` 中的 `video_extensions` 列表

**Q: 如何调整最小文件大小？**
A: 设置环境变量 `MIN_VIDEO_SIZE_BYTES` 或修改 `rename_rules.yaml` 中的 `min_file_size_bytes`

### 扁平化相关
**Q: 为什么所有文件都移动到了根目录？**
A: 这是默认的扁平化行为，旨在简化文件结构。所有子目录中的文件会自动移动到指定的根目录。

**Q: 如何保持原有的目录结构？**
A: 当前版本默认启用扁平化，如需保持目录结构，请考虑分别处理各个子目录。

**Q: 扁平化时遇到同名文件怎么办？**
A: 使用 `--conflict-resolution rename` 参数，系统会自动添加序号避免冲突。

### 安全性相关
**Q: 工具会覆盖现有文件吗？**
A: 绝对不会。工具设计为绝不覆盖现有文件，确保数据安全。

**Q: 如何预览操作而不实际执行？**
A: 使用 `--dry-run` 参数进行预览模式。

**Q: 如何回滚操作？**
A: 使用 `--log-operations` 记录操作，然后使用 rollback 工具进行回滚。

### 配置相关
- 未找到规则文件：若输出提示"未找到重命名规则文件: ..."，请确认 RENAME_RULES_PATH 或默认配置文件存在
- 想仅处理某类扩展名：在 settings.video_extensions 中调整为所需列表
- 想降低最小大小阈值用于测试：设置环境变量 `MIN_VIDEO_SIZE_BYTES=1`

## 开发与测试
- 单元测试使用 pytest 并已覆盖核心行为（规则加载、规范化、批量重命名、CLI）
- 修改配置或逻辑后建议运行：
```
pytest -q