# Feature: Scan/Merge 职责分离与文件移动检测设计

## 收敛版设计更新（简化语义与字段）

本节根据最新共识补充并收敛设计，以保持“低复杂度、清晰语义、最小改动”。不修改现有工作流，仅明确字段与表职责，并给出场景验证。若与后文旧草案存在不一致，以本节规则为准。

### 核心取舍
- `video_info.file_status`统一为三态：`present` / `missing` / `ignore`。
- `last_scan_time`更名为合并维度的时间：`last_merge_time`（语义更清晰），不记录真实扫描时间。
- 统一命名为 `video_code`（而非 `code`），在各表与示例中保持一致。
- `video_master_list`字段最小化：`video_code`（唯一）、`status`（`present`/`deleted`）、`update_time`；“最新 `logical_path`”可采用冗余字段`latest_logical_path`或在查询时通过 `video_info` 的 `present` 记录计算（推荐查询计算）。
- `merge_history`为文件级日志，事件三类：`insert_new`、`insert_ignore`、`mark_missing`；`scan_id`用于关联到`scan_history`，若无法检索到则置空（`NULL`）。
- `scan_history`在“扫描时”维护；`merge_history`在“合并时”维护，避免角色混淆。
- 指纹采用轻量方案，不读视频内容：`created_time + video_code + duration + width + height + bit_rate + size`（规范化组成，附版本前缀如`v1:`）。
- 全局信任指纹：默认不存在同指纹的真实多副本；如偶发存在，后续可人工检索处理。
- `video_master_list`不使用指纹；`video_info`与`video_master_list`均存`video_code`并以其为用户视角的唯一业务标识。

### 表职责与字段（DDL草案）
- `video_info`（底层事实表）
  - 重点新增字段：
    - `video_code TEXT`（统一小写存储，查询使用 NOCASE）
    - `file_fingerprint TEXT`
    - `file_status TEXT`（`present`/`missing`/`ignore`）
    - `last_merge_time INTEGER`（UNIX 时间戳）
  - 推荐索引：`idx_video_info_video_code`、`idx_video_info_fingerprint`、`idx_video_info_status`、`idx_video_info_last_merge_time`

  - 全局不变式与约束：
    - 每个指纹始终仅有一条“非 `ignore` 主记录”（`file_status ∈ {present, missing}`）；允许存在若干历史 `ignore` 记录。
    - 当新路径出现且旧主记录为`present`时：插入“新主记录”（`file_status=present`），并将“旧主记录”标记为`ignore`；不修改旧记录的任何时间戳（含`last_merge_time`、`updated_time`）。
    - 查询与报表默认过滤 `file_status=ignore`，必要时提供人工检索入口。

- `video_master_list`（用户报表主表）
  - 字段（最小化）：
    - `video_code TEXT UNIQUE NOT NULL`
    - `status TEXT NOT NULL CHECK (status IN ('present','deleted'))`
    - `update_time INTEGER NOT NULL`（UNIX 时间戳）
    - 可选冗余：`latest_logical_path TEXT NULL`
  - 索引：唯一 `unique_master_video_code`，普通 `idx_master_status`

- `scan_history`（扫描日志，扫描时写入）
  - 字段建议（与现有保持一致或补充）：`id`、`scan_time`、`scan_path`、`csv_file`、`csv_fingerprint`、`files_found`、`files_processed`、`tags`、`logical_path`

- `merge_history`（文件级合并日志，合并时写入）
  - 字段：
    - `id INTEGER PRIMARY KEY AUTOINCREMENT`
    - `merge_time INTEGER NOT NULL`（UNIX 时间戳）
    - `scan_id INTEGER NULL`（指向 `scan_history.id`，若无法解析则 `NULL`）
    - `event_type TEXT NOT NULL`（`insert_new` | `insert&ignore` | `mark_missing`）
    - `video_id INTEGER`（可选，指向 `video_info.id`）
    - `video_code TEXT`、`file_path TEXT`、`logical_path TEXT`、`file_fingerprint TEXT`
  - 索引：`idx_merge_scan(scan_id, merge_time)`、`idx_merge_fingerprint(file_fingerprint)`、`idx_merge_video_code(video_code)`、`idx_merge_video_id(video_id)`
  - `scan_id`解析策略：优先按 `csv_file` 精确匹配 `scan_history`；不命中则按 `csv_fingerprint` 或 `scan_time` 近邻匹配；均失败则置 `NULL`。

### 指纹规范（轻量版）
- 组成：`created_time + code + duration + width + height + bit_rate + size`
- 规范化建议：
  - `code`统一小写、去扩展名与空白；查询 `COLLATE NOCASE`；
  - `duration`保留到小数点后2位；`bit_rate`按`kbps`取整；`size`原值；
  - `created_time`优先文件出生时间，不可用时退化为修改时间。
- 版本前缀：如 `v1:<md5(payload)>`，便于未来升级。

### 合并行为与路径更新规则（简化版）
1) 读取 CSV（关联 `scan_id`），为每条记录生成指纹与 `code`。
2) 比对 `video_info`：
   - 新出现的指纹：`insert` → 写入/更新为 `present`，更新 `file_path`、`last_merge_time`，写 `merge_history.insert`。
   - 已存在指纹且路径相同：仅刷新 `last_merge_time`（不写日志）。
   - 已存在指纹但路径不同：
     - 若旧主记录当前为 `missing`，则更新该主记录的 `file_path` 为新路径，状态置为 `present`，刷新 `last_merge_time`，写 `merge_history.insert`（“缺失→找回/移动后的出现”）。
     - 若旧主记录当前为 `present`，则插入一条“新主记录”（`is_ignore=0`,`file_status=present`，携带新路径），同时将旧主记录标记为 `ignore`（`is_ignore=1`）；不修改旧记录的任何时间戳（包括 `last_merge_time`、`updated_time`）。不保留“多副本”的双主状态。
3) 对数据库中上次在同一扫描范围下为 `present`但本次 CSV 未出现的记录：标记为 `missing`，刷新 `last_merge_time`，写 `merge_history.mark_missing`。

> 注意：不强制底层“判定移动”。移动仅作为报表层的分析结论（近邻 `mark_missing + insert` 同指纹）呈现，不引入额外事件类型或字段。

### 场景验证（避免脏数据的边界与策略）
以下场景用于验证“当发现 `missing` 记录且指纹一致时更新路径与状态”的安全性与边界。

1) 真移动（安全更新路径）
- 场景：文件从`/A/old.mp4`移到`/B/new.mp4`，两次合并分别基于不同目录的 CSV。
- 行为：第一轮 `/A` 合并把旧记录标记 `missing`；第二轮 `/B` 合并发现同指纹，更新该记录 `file_path=/B/new.mp4`，状态`present`，写 `insert`。
- 结论：安全，无脏数据；同一实体仅路径变更。

2) 外接盘断连后恢复（安全恢复）
- 场景：外接盘丢失导致上轮合并把记录标记 `missing`，下一轮合并盘恢复，文件路径可能相同或不同。
- 行为：恢复后出现同指纹 → 更新原记录为 `present`，根据实际路径更新 `file_path`。
- 结论：安全，无脏数据；“缺失→找回”的典型流程。

3) 同指纹的多副本同时存在（按规则退役旧主记录）
- 场景：同一视频存在两个物理副本 `/A/file.mp4` 与 `/B/file.mp4`，仅 `/B` 被合并。
- 行为：基于“信任指纹”，在检测到新路径且旧主记录为 `present` 时，直接插入“新主记录”，并将旧主记录标记为 `ignore`（隐藏旧副本）。
- 影响：真实的多副本事实被隐藏（旧副本退役为 `ignore`）；如需处理，后续可通过检索 `ignore` 记录进行人工清理或恢复。
- 结论：符合“信任指纹、单主记录”的取舍；不为多副本场景增加复杂性或安全闸门。

4) 仅重命名（不视为同指纹）
- 场景：文件仅重命名导致 `code` 变化（如 `ABC-123` → `ABC-123X`），其组成指纹包含 `code`。
- 行为：新文件指纹不同 → 视为新增；旧记录在未出现的范围标记 `missing`。
- 结论：不做路径更新，避免把不同业务标识的文件合并为同一实体。

5) 指纹罕见碰撞（审慎对待）
- 场景：极少数情况下不同文件的指纹值相同（全部组合字段一致）。
- 行为：按“同指纹同实体”处理可能带来误合并风险。
- 策略：在报表层保留“异常对比”入口（大小、分辨率、码率等）供人工复核；必要时后续引入升级指纹版本（如增加一个更稳健组件）。
- 结论：风险可控，发生率极低；通过人工复核与升级路径缓解。

6) 部分扫描范围（缺失的局部定义）
- 场景：只合并目录 `/A` 的 CSV，数据库中还有 `/B` 的历史记录。
- 行为：`missing` 的定义仅相对本次扫描范围（由 `scan_id` 表达）；不会影响其他范围的 `present` 记录。
- 结论：缺失语义清晰，不会引入全局脏数据。

7) 用户手动清理路径后再次出现（安全找回）
- 场景：用户手动删除或搬迁后，文件在另一目录再次出现。
- 行为：先被标记 `missing`，后因同指纹出现在新目录更新为 `present` 并刷新路径。
- 结论：安全；符合“缺失→找回”的预期。

### 防重复下载与全局视角（与 master 对齐）
- 下载前以 `video_master_list.code` 为准：若 `status=active` 且存在任一 `video_info.present`，则拒绝重复下载。
- 当 `status=deleted` 时，按业务策略决定是否允许重新下载（可用状态细分表达）。
- 历史 code-only 清单可直接导入到 `video_master_list`，作为全局报表的主数据源。

### 实施提示（后续阶段）
- 保持 `scan` 原子性：扫描时写入 `scan_history`，`merge` 时写入 `merge_history`。
- 在路径更新时不做同指纹的 `present` 复核；若新路径出现且旧主记录为 `present`，直接退役旧主记录为 `ignore` 并插入新主记录。
- 指纹生成统一封装为单点函数（带版本前缀），确保各阶段一致性。


## 摘要
- 明确架构：`scan` 仅生成 CSV（原子操作，不触库）；`merge` 读取 CSV 与数据库比对，识别新增/缺失/移动并更新库。
- 用轻量级指纹（文件名、文件大小、创建时间、时长）在 `merge` 阶段识别文件移动，避免误标记为删除。
- **新增 `code` 字段**：从文件名提取视频编码（如 `ABC-123.mp4` → `ABC-123`），作为视频的唯一业务标识，用于重复下载防护。
- **总清单管理**：新增 `video_master_list` 表记录所有视频 code 的状态（active/deleted/duplicate），支持导入 code-only 清单预先标记已删除视频。
- **重复下载防护**：通过 code 识别重复下载，提供重复文件管理和删除状态追踪，避免重复下载和下载已删除视频。
- **智能重复管理**：识别同一 code 的多个文件，基于文件大小等信息提供保留建议，帮助用户决策。
- 最小化数据库变更：为 `video_info` 增加 `code`、`file_fingerprint`、`file_status`、`last_scan_time` 字段及索引；新增 `video_master_list` 和 `merge_history` 表。
- 与现有 CLI 文档保持一致：沿用当前的 CSV 命名与工作流（见 `CLI_DEMO.md`），不改变 `scan` 的用户体验。

---

## 背景与前因后果

### 初始误解
- 早期提议将 `scan` 扩展为“扫描并输出扫描结果（新增/缺失等）”，这与现有工具设计不符。
- 用户明确指出：`scan` 的职责只是生成 CSV；只有在 `merge` 阶段，系统才根据 CSV 与数据库进行增量识别（新增、删除、移动）。

### 用户关键诉求
- 保持 `scan` 原子性与独立性：不触库、不关心历史状态。
- 识别“文件移动而非删除”的情况：`not_found` 应尽量友好，能正确合并“同一文件移动到新路径”的记录。
- CSV 命名应继续沿用现有规范，避免对现有工作流造成破坏。
- 尽量避免昂贵的文件内容哈希（I/O 读整文件），优先采用轻量指纹识别方案。

### 设计转向
- 方案改为在 `merge` 阶段实现智能对比与移动检测，`scan` 不做任何状态判断。
- 采用轻量指纹组合，实现跨目录、跨扫描顺序的稳健移动识别。

---

## 目标与非目标

### 目标
- 职责清晰：`scan` 仅生成 CSV；`merge` 完成状态识别与数据库更新。
- 识别文件新增、缺失（not_found）、移动（更新路径）。
- **重复下载防护**：通过 `code` 识别重复下载，避免重复下载和下载已删除视频。
- **总清单管理**：维护所有视频 code 的状态（active/deleted/duplicate），支持预先导入已删除视频清单。
- **重复文件管理**：识别同一 code 的多个文件，基于文件大小、分辨率、码率等信息提供保留建议。
- **删除状态追踪**：记录用户主动删除的视频 code，防止重复下载已删除内容。
- **智能合并建议**：对于重复文件，提供详细对比信息（文件大小、质量等），辅助用户决策。
- 提供清晰的合并报告与历史记录。
- 保留现有工作流与 CSV 命名规范。

### 非目标
- 不引入昂贵的内容哈希（如整文件 SHA256）。
- 不在 `scan` 阶段触及数据库或进行增量推断。
- 不将"重命名"强制等同于"移动"（见风险与边界）。
- **不自动删除重复文件**（仅提供识别和建议，由用户决定）。
- 不自动判断视频质量优劣（仅提供客观指标对比）。

---

## 术语与职责界定
- `scan`：只扫描指定目录，提取视频元数据，输出到 CSV 文件；不更新数据库。
- `merge`：读取一个或多个 CSV，与数据库进行比对，识别并更新文件状态（新增、缺失、移动）。
- `code`：从文件名提取的视频业务编码（如 `ABC-123.mp4` → `ABC-123`），作为视频的唯一业务标识，用于重复下载防护。
- `总清单（master_list）`：记录所有已知视频 code 及其状态的主表，用于重复下载防护和删除状态追踪。
- `code-only 清单`：仅包含视频 code 的清单文件，用于预先标记已删除的视频，防止重复下载。
- 文件状态（在 video_info 表中）：
  - `scanned`：最近一次合并后仍存在且路径有效。
  - `not_found`：在数据库中存在，但在最近一次合并的 CSV 中未出现（可能删除或暂未扫描到）。
- 视频状态（在总清单中）：
  - `active`：当前存在有效文件。
  - `deleted`：已被用户删除，不应重复下载。
  - `duplicate`：存在多个文件副本，需要用户决策保留哪个。

---

## 架构设计

### scan（原子操作）
- 输入：扫描根路径、可选标签、逻辑路径等元数据注入参数。
- 输出：CSV 文件（沿用 `CLI_DEMO.md` 中的命名与输出目录约定）。
- 行为：
  - 枚举视频文件，提取元数据（分辨率、时长、编解码、大小等）。
  - **提取 `code`**：从文件名中提取业务编码（如 `ABC-123.mp4` → `ABC-123`）。
  - 生成轻量指纹 `file_fingerprint`（见下文）。
  - 写入 CSV；不触及数据库、不做状态判断。

### merge（智能合并）
- 输入：CSV 文件路径、数据库路径（默认 `output/video_info_collector/database/video_database.db`）。
- 输出：合并报告（终端输出或日志文件），数据库状态更新，`merge_history` 记录。
- 核心流程：
  1. 读取 CSV 新数据集合 `N`。
  2. 读取数据库现有数据集合 `E`。
  3. 构建指纹索引：`map_f_N` 与 `map_f_E`。
  4. **构建 code 索引**：`map_c_N` 与 `map_c_E`，用于重复检测。
  5. **检查删除状态**：对每个 `n ∈ N`，检查其 code 在总清单中是否标记为 `deleted`，如是则警告用户。
  6. 对每个 `n ∈ N`：
     - 若 `n.fingerprint ∈ map_f_E` 且 `n.file_path != e.file_path` → 认定为移动，更新数据库路径。
     - 若 `n.fingerprint ∈ map_f_E` 且路径相同 → 认定为无变化。
     - 若 `n.fingerprint ∉ map_f_E` → 认定为新增，插入。
     - **重复检测**：若 `n.code` 在数据库中已存在但指纹不同 → 标记为重复文件，提供对比信息。
  7. 对每个 `e ∈ E`：若 `e.fingerprint ∉ map_f_N` → 认定为缺失，标记为 `not_found`（保留记录）。
  8. **更新总清单**：同步 `video_master_list` 表，更新各 code 的状态（active/deleted/duplicate）。
  9. **生成重复文件报告**：对于重复文件，提供详细对比（文件大小、分辨率、码率等）和保留建议。
  10. 记录合并统计并写入 `merge_history`。

---

## CSV 命名与存储
- 沿用现有规范与目录结构（参考 `tools/video_info_collector/CLI_DEMO.md`）：
  - 输出目录位于 `output/video_info_collector/csv/`（或用户自定义）。
  - 文件名与工作流保持一致，不引入新的命名格式。
- 每个 CSV 行至少包含：`file_path`、`filename`、`code`、`file_size`、`duration`、`created_time`、`file_fingerprint`，以及其他视频元数据与逻辑标签。
- **新增字段说明**：
  - `code`：从文件名提取的视频业务编码，用于重复下载防护。
  - `file_fingerprint`：轻量级文件指纹，用于移动检测。

## Code 提取规则
- **提取逻辑**：从文件名中提取视频业务编码，去除扩展名。
- **示例**：
  - `ABC-123.mp4` → `ABC-123`
  - `DEF-456.mkv` → `DEF-456`
  - `GHI_789.avi` → `GHI_789`
- **边界情况**：
  - 若文件名不符合预期格式，使用完整文件名（去扩展名）作为 code。
  - 支持自定义提取规则（正则表达式配置）。

---

## 文件唯一性识别（轻量指纹）
- 组成字段：
  - `filename`（含扩展名）
  - `file_size`（字节）
  - `created_time`（文件创建时间戳；若不可用，回退为修改时间）
  - `duration`（时长，秒）
- 生成方式：将上述字段拼接为字符串，取 `MD5`（或 `SHA1`，任选其一）作为 `file_fingerprint`。
- 设计权衡：
  - 优点：无需读取文件内容，几乎零 I/O 成本，速度快。
  - 风险：字段偏差（如不同文件同名同大小同创建时间且时长接近）可能导致极罕见冲突；可在未来通过新增字段或“内容哈希兜底”策略扩展。

---

## Code-Only 清单导入与删除状态管理

### 功能概述
- 支持导入仅包含视频 code 的清单文件，用于预先标记已删除的视频。
- 防止用户重复下载已删除的视频内容。
- 维护总清单（`video_master_list`）记录所有已知视频 code 的状态。

### 导入流程
1. **清单格式**：支持简单的文本文件或 CSV 格式，每行一个 code。
   ```
   ABC-123
   DEF-456
   GHI-789
   ```
2. **导入命令**：`merge --import-deleted <清单文件路径>`
3. **处理逻辑**：
   - 读取清单中的所有 code。
   - 在 `video_master_list` 中标记这些 code 为 `deleted` 状态。
   - 若 code 已存在且状态为 `active`，询问用户是否覆盖。
   - 记录导入操作到 `merge_history`。

### 删除状态检查
- 在 `merge` 过程中，检查新扫描的文件 code 是否在总清单中标记为 `deleted`。
- 若发现已删除的 code，输出警告信息：
  ```
  警告：发现已删除视频 ABC-123 (文件: /path/to/ABC-123.mp4)
  建议：考虑是否需要重新删除此文件
  ```

### 总清单表设计（video_master_list）
```sql
CREATE TABLE IF NOT EXISTS video_master_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'deleted' | 'duplicate'
    file_count INTEGER DEFAULT 0,           -- 当前存在的文件数量
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT                              -- 用户备注（可选）
);

CREATE INDEX IF NOT EXISTS idx_master_list_code ON video_master_list(code);
CREATE INDEX IF NOT EXISTS idx_master_list_status ON video_master_list(status);
```

---

## 移动检测算法（在 merge 阶段）

伪代码：
```python
existing_by_fp = {e.file_fingerprint: e for e in existing}
csv_by_fp = {n.file_fingerprint: n for n in new}

for fp, n in csv_by_fp.items():
    if fp in existing_by_fp:
        e = existing_by_fp[fp]
        if e.file_path != n.file_path:
            # 移动：更新数据库中的 file_path，保留其余元数据
            mark_as_moved(e, new_path=n.file_path)
        else:
            mark_as_unchanged(e)
    else:
        # 新增：插入
        insert_new(n)

# 缺失：数据库存在但 CSV 不在
csv_fp_set = set(csv_by_fp.keys())
for e in existing:
    if e.file_fingerprint not in csv_fp_set:
        mark_as_not_found(e)
```

跨扫描顺序的稳健性：
- 先扫描“新目录”或“旧目录”均可；只要指纹一致，即可在合并时识别为移动并更新路径。
- 若移动发生于多个合并之间，后续合并会自动修正路径并清除 `not_found` 状态（当同一指纹再次出现时）。

---

## 缺失文件处理策略
- 合并时未出现在 CSV 的数据库记录将标记为 `not_found`，但仍保留数据（不删除）。
- 若后续某次合并出现相同指纹但新路径不同：认定为“找回的移动文件”，更新路径并恢复为 `scanned`。
- 报告中显示缺失文件的数量与代表性列表（可分页）。

---

## 数据库变更（最小化）

### 现有主表：`video_info`
字段回顾（节选）：`id`, `file_path`（UNIQUE, NOT NULL）, `filename`, `width`, `height`, `resolution`, `duration`, `video_codec`, `audio_codec`, `file_size`, `bit_rate`, `frame_rate`, `logical_path`, `created_time`, `updated_time`。

### 新增字段与索引
这些字段已经包含在最新的表定义中：
- `code TEXT` -- 视频业务编码
- `file_fingerprint TEXT` -- 轻量级文件指纹  
- `file_status TEXT DEFAULT 'scanned'` -- 'scanned' | 'not_found'
- `last_scan_time TEXT` -- 最后扫描时间

相关索引：
```sql
CREATE INDEX IF NOT EXISTS idx_video_info_code ON video_info(code);
CREATE INDEX IF NOT EXISTS idx_video_info_fingerprint ON video_info(file_fingerprint);
CREATE INDEX IF NOT EXISTS idx_video_info_status ON video_info(file_status);
```

### 新增表：`video_master_list`（总清单）
```sql
CREATE TABLE IF NOT EXISTS video_master_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,                      -- 视频业务编码
    status TEXT NOT NULL DEFAULT 'active',          -- 'active' | 'deleted' | 'duplicate'
    file_count INTEGER DEFAULT 0,                   -- 当前存在的文件数量
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,      -- 首次发现时间
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,    -- 最后更新时间
    notes TEXT                                       -- 用户备注（可选）
);

CREATE INDEX IF NOT EXISTS idx_master_list_code ON video_master_list(code);
CREATE INDEX IF NOT EXISTS idx_master_list_status ON video_master_list(status);
```

### 新增表：`merge_history`
```sql
CREATE TABLE IF NOT EXISTS merge_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    csv_file TEXT NOT NULL,
    merge_time TEXT DEFAULT CURRENT_TIMESTAMP,
    new_files INTEGER DEFAULT 0,
    moved_files INTEGER DEFAULT 0,
    unchanged_files INTEGER DEFAULT 0,
    missing_files INTEGER DEFAULT 0,
    duplicate_files INTEGER DEFAULT 0,              -- 重复文件数量
    deleted_warnings INTEGER DEFAULT 0,             -- 已删除视频警告数量
    operation_type TEXT DEFAULT 'merge',            -- 'merge' | 'import_deleted'
    status TEXT DEFAULT 'completed'
);
```

说明：
- 保留现有 `scan_history`（当前实现已存在），`merge_history` 用于单独追踪合并事件。

---

## 合并报告输出示例
```
合并结果:
────────────┬───────+
| 操作类型   | 数量  |
────────────┼───────+
| 新增文件   | 15    |
| 文件移动   | 3     |
| 无变化文件 | 127   |
| 缺失文件   | 2     |
| 重复文件   | 4     |
| 删除警告   | 1     |
────────────┴───────+

文件移动详情:
• ABC-123.mp4: /old/path → /new/path
• DEF-456.mkv: /media/old → /media/new
• GHI-789.avi: /temp → /storage

缺失文件 (not_found):
• XYZ-001.mp4 (上次扫描: 2024-01-15)
• ABC-999.mkv (上次扫描: 2024-01-14)

重复文件检测:
• Code: ABC-123 (2个文件)
  - 文件1: /path1/ABC-123.mp4 (1.2GB, 1080p, 5000kbps) ⭐ 推荐保留
  - 文件2: /path2/ABC-123.mkv (800MB, 720p, 3000kbps)
• Code: DEF-456 (2个文件)
  - 文件1: /path3/DEF-456.mp4 (2.1GB, 1080p, 8000kbps) ⭐ 推荐保留
  - 文件2: /path4/DEF-456.avi (1.5GB, 1080p, 6000kbps)

删除状态警告:
⚠️  发现已删除视频: GHI-789 (文件: /new/GHI-789.mp4)
   建议：考虑是否需要重新删除此文件
```

---

## CLI 接口与用户体验

### scan 命令（保持不变）
- 功能：只生成 CSV，不触及数据库。
- 新增输出：在 CSV 中包含 `code` 和 `file_fingerprint` 字段。

### merge 命令（增强功能）
- **基本合并**：`merge <csv_file>`
  - 支持合并多个 CSV（顺序无关）。
  - 输出合并统计、移动详情、重复文件检测。
  - 维护 `merge_history` 和 `video_master_list`。

- **导入删除清单**：`merge --import-deleted <清单文件>`
  - 导入 code-only 清单，标记已删除视频。
  - 支持文本文件或 CSV 格式。
  - 防止重复下载已删除内容。

- **重复文件管理**：`merge --show-duplicates`
  - 显示所有重复文件的详细对比信息。
  - 提供基于文件大小、分辨率、码率的保留建议。

### 查询命令（新增功能）
- `--list-missing`：列出 `not_found` 文件。
- `--list-duplicates`：列出所有重复文件组。
- `--list-deleted`：列出总清单中标记为已删除的 code。
- `--merge-history`：查看最近合并统计。
- `--master-list [--status=active|deleted|duplicate]`：查看总清单，可按状态过滤。

### 用户体验改进
- **智能建议**：对重复文件提供保留建议（基于文件大小、质量等）。
- **删除警告**：发现已删除视频时提供明确警告和建议。
- **详细报告**：提供清晰的操作统计和文件对比信息。
- **交互确认**：导入删除清单时，对冲突情况提供用户选择。

---

## 风险与边界
- `created_time` 在不同文件系统语义差异：必要时回退为 `modified_time`。
- 仅移动不重命名：指纹包含 `filename`，若发生重命名，可能被识别为“新增+缺失”而非“移动”。这是有意的边界，避免误合并不同文件。后续可通过可选策略支持“重命名识别”。
- 极罕冲突：轻量指纹存在理论碰撞可能性；可在未来引入可选“内容哈希兜底”以进一步降低风险。

---

## 实施步骤（开发任务）
- 更新 `merge` 实现：增加指纹比对与路径更新逻辑。
- 更新 `sqlite_storage.py`：
  - 新增 `merge_history` 表创建逻辑。
- 更新 CLI：
  - `--merge` 输出统计与详情。
  - 可选：实现 `--list-missing` 与 `--merge-history`。
- 测试：
  - 覆盖新增、移动、缺失三类用例与跨顺序场景。

---

## 附录

### 指纹生成示例（伪代码）
```python
import hashlib

def generate_file_fingerprint(filename, file_size, created_time, duration):
    payload = f"{filename}|{file_size}|{created_time}|{duration}"
    return hashlib.md5(payload.encode()).hexdigest()
```

### 合并伪代码
```python
def smart_merge(csv_rows, db_rows):
    existing_by_fp = {e.file_fingerprint: e for e in db_rows}
    csv_by_fp = {n.file_fingerprint: n for n in csv_rows}

    stats = dict(new=0, moved=0, unchanged=0, missing=0)

    # 处理 CSV → DB
    for fp, n in csv_by_fp.items():
        if fp in existing_by_fp:
            e = existing_by_fp[fp]
            if e.file_path != n.file_path:
                update_path(e.id, n.file_path)
                stats['moved'] += 1
            else:
                stats['unchanged'] += 1
            mark_scanned(e.id)
        else:
            insert_row(n)
            stats['new'] += 1

    # 处理 DB 缺失
    csv_fp_set = set(csv_by_fp.keys())
    for e in db_rows:
        if e.file_fingerprint not in csv_fp_set:
            mark_not_found(e.id)
            stats['missing'] += 1

    write_merge_history(stats)
    return stats
```

---

## 与现有文档的对齐
- 遵循 `CLI_DEMO.md` 推荐工作流程：先 `scan` 产出 CSV，人工检查后再 `merge` 入库。
- 不改变现有参数与行为，仅在 `merge` 增强智能对比与报告能力。

---

## 验收标准（Acceptance Criteria）

### 基础功能验收
- `scan` 不触库，仅生成 CSV；行为与现有文档一致。
- `merge` 能稳定识别新增、移动、缺失，且移动更新路径而非误删。
- 数据库新增列与索引创建成功；历史数据能逐步补齐指纹。
- 合并报告清晰、数量正确；`merge_history` 正确记录统计。
- 跨不同合并顺序（先新目录或先旧目录）仍能识别移动并合并一致。

### 新功能验收
- **Code 提取与存储**：
  - 能正确从文件名提取 code（如 `ABC-123.mp4` → `ABC-123`）。
  - 处理边界情况（无扩展名、多个连字符、特殊字符）。
  - CSV 和数据库中正确存储 code 字段。

- **重复检测功能**：
  - 能识别相同 code 但不同指纹的重复文件。
  - 提供详细的文件对比信息（大小、分辨率、码率等）。
  - 给出基于文件质量的保留建议。
  - 重复文件状态正确更新到 `video_master_list`。

- **删除状态管理**：
  - 能成功导入 code-only 删除清单。
  - 对已删除 code 的新文件提供警告。
  - 总清单正确记录删除状态。
  - 防止重复下载已删除内容。

- **总清单功能**：
  - `video_master_list` 表正确创建和维护。
  - 状态字段（active/deleted/duplicate）准确更新。
  - 查询命令能正确显示各状态的 code。

- **CLI 接口验收**：
  - 所有新增命令参数正常工作。
  - 报告输出格式清晰易读。
  - 交互确认功能正常响应用户选择。
  - 错误处理和用户提示友好明确。