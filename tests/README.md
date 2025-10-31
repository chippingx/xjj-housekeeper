# 测试说明

本目录包含 xjj_housekeeper 项目的测试代码和测试数据。

## 目录结构

```
tests/
├── README.md                    # 本文件
├── conftest.py                  # pytest 配置
├── original_folder/             # 回归测试数据目录（不可修改）
│   ├── TST-003-FHD/
│   │   └── TST-003-FHD.mp4     # 标准格式文件
│   ├── TST-004ch/
│   │   └── TST-004ch.mp4       # 需要清理 "ch" 后缀
│   ├── TST-005/
│   │   └── TST-005.mp4         # 已标准化文件
│   ├── TST-006_CH.HD/
│   │   └── TST-006_CH-nyap2p.com.mp4  # 复杂前后缀
│   ├── TST-001.mp4             # 根目录标准文件
│   └── btnets.net_TST-002.mp4  # 网站前缀需清理
└── tool_filename_formatter/     # 单元测试
    ├── test_filename_formatter.py
    └── test_cli_filename_formatter.py
```

## 回归测试数据 (original_folder)

### 重要说明
⚠️ **`original_folder` 目录下的文件不得修改！**

这个目录包含用于回归测试的"黄金标准"测试数据，模拟真实场景中常见的文件名模式。

### 测试用例说明

| 文件路径 | 测试场景 | 预期结果 |
|---------|---------|---------|
| `TST-003-FHD/TST-003-FHD.mp4` | 标准格式文件 | 保持不变 |
| `TST-004ch/TST-004ch.mp4` | 需要清理 "ch" 后缀 | `TST-004.mp4` |
| `TST-005/TST-005.mp4` | 已标准化文件 | 保持不变 |
| `TST-006_CH.HD/TST-006_CH-nyap2p.com.mp4` | 复杂前后缀 | `TST-006.mp4` |
| `TST-001.mp4` | 根目录标准文件 | 保持不变 |
| `btnets.net_TST-002.mp4` | 网站前缀 | `TST-002.mp4` |

### 文件格式
- 所有 mp4 文件都是最小化的假文件（2KB），但保持有效的 mp4 格式
- 这样既节省存储空间，又能通过工具的文件类型检查

## 如何进行回归测试

### 1. 手动测试
```bash
# 1. 拷贝测试数据到临时目录
cp -r tests/original_folder /tmp/test_data

# 2. 设置最小文件大小为1字节（便于测试小文件）
export MIN_VIDEO_SIZE_BYTES=1

# 3. 运行文件名清理工具
python -m tools.filename_formatter /tmp/test_data

# 4. 检查结果
find /tmp/test_data -name "*.mp4" | sort

# 5. 清理临时文件
rm -rf /tmp/test_data
```

### 2. 自动化测试
```bash
# 运行所有单元测试
pytest -q

# 运行特定测试
pytest tests/tool_filename_formatter/ -v
```

## 添加新的测试用例

如果需要添加新的测试场景：

1. **不要修改 `original_folder` 中的现有文件**
2. 在 `original_folder` 中添加新的测试文件：
   ```bash
   # 创建新的测试目录和文件
   mkdir tests/original_folder/NEW-PATTERN
   
   # 创建最小mp4文件
   ffmpeg -f lavfi -i testsrc=duration=0.1:size=32x32:rate=1 \
          -c:v libx264 -t 0.1 -pix_fmt yuv420p \
          tests/original_folder/NEW-PATTERN/new-pattern-file.mp4 -y
   ```
3. 更新本文档中的测试用例说明表格
4. 在单元测试中添加对应的测试代码

## 测试最佳实践

1. **保护测试数据**：永远不要直接在 `original_folder` 上运行清理工具
2. **使用临时目录**：每次测试都拷贝数据到临时目录
3. **清理环境**：测试完成后清理临时文件
4. **环境变量**：使用 `MIN_VIDEO_SIZE_BYTES=1` 来测试小文件
5. **验证结果**：不仅要检查重命名是否成功，还要验证文件内容完整性

## 故障排除

### 常见问题

1. **文件大小限制**：如果测试文件被跳过，检查 `MIN_VIDEO_SIZE_BYTES` 环境变量
2. **权限问题**：确保对测试目录有读写权限
3. **路径问题**：使用绝对路径避免相对路径问题

### 调试技巧

```bash
# 查看详细的重命名过程
python -c "
from tools.filename_formatter import FilenameFormatter
fmt = FilenameFormatter(min_file_size=1)
results = fmt.rename_in_directory('/tmp/test_data', include_subdirs=True)
for r in results:
    print(f'{r.status}: {r.original} -> {r.new}')
"
```