# 文件名规范化工具（filename_formatter）

批量清理并规范化视频文件名，支持规则驱动的字符串替换与标准化格式（示例：`ABC-123.mp4`）。工具以“安全重命名”为第一原则：不覆盖已有文件，可选记录操作日志并提供回滚工具。

## 关键特性

- 默认递归扫描子目录，并将结果扁平化输出到根目录（可通过代码参数关闭；CLI 默认开启）
- 按扩展名过滤（默认 `.mp4/.mkv/.mov`，可配置）
- 按最小文件大小过滤（默认 100MB，避免处理无效小文件）
- 冲突处理：跳过（默认）或自动改名追加序号
- 预览模式：仅展示将执行的操作，不实际改动
- 操作日志与回滚：可生成 `.operation_log_*.json` 并按日志回滚

## 配置文件

### 规则文件位置与优先级

`rename_rules.yaml` 属于用户本地配置，已加入 `.gitignore`，不应提交到仓库。

- 推荐做法：复制示例文件并按需修改
  - 示例：`tools/filename_formatter/rename_rules.yaml.example`
  - 用户文件：`tools/filename_formatter/rename_rules.yaml`
- 或者：设置环境变量 `RENAME_RULES_PATH` 指向任意 YAML 文件（绝对路径或相对项目根）

### YAML 结构

```yaml
settings:
  video_extensions: [".mp4", ".mkv", ".mov"]
  min_file_size_bytes: 104857600

rename_rules:
  - pattern: "example.com@"
    replace: ""
  - pattern: "ch.mp4"
    replace: ".mp4"
```

说明：
- `rename_rules` 为顺序执行的简单 `str.replace`（非正则）
- 规则应用后会进行标准化格式化（字母大写 + 字母数字间连字符）

## CLI 用法

```bash
python -m tools.filename_formatter <目录路径> [选项]
```

可用参数：
- `--dry-run`：预览模式（不修改文件）
- `--conflict-resolution {skip,rename}`：冲突策略（默认 `skip`）
- `--log-operations`：记录操作日志（仅在非预览模式下写入）
- `--verify-size`：轻量级验证（在执行重命名后检查文件大小一致性）

环境变量：
- `RENAME_RULES_PATH`：规则文件路径
- `MIN_VIDEO_SIZE_BYTES`：覆盖最小文件大小阈值
- `HUMAN_LOG_INTERVAL_SECS`：输出节奏控制（可选，避免一次性刷屏）

## 回滚操作

当使用 `--log-operations` 执行重命名后，会在处理目录下生成 `.operation_log_*.json`。

```bash
python -m tools.filename_formatter.rollback <日志文件路径> [--dry-run]
```

回滚同样遵循安全原则：若源路径已存在会跳过，不覆盖文件。
