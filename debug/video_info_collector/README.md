# Video Info Collector Debug 脚本

本目录包含视频信息收集器模块的调试脚本。

## 调试脚本说明

### debug_duplicates.py
**用途**: 调试重复文件检测逻辑
- 分析文件指纹计算过程
- 检查重复文件识别准确性
- 验证去重算法的有效性

### debug_full_merge.py
**用途**: 调试完整的合并检测流程
- 验证智能合并管理器的完整工作流程
- 检查文件状态变更逻辑
- 分析合并历史记录

### debug_db_status.py (从根目录移动)
**用途**: 调试数据库状态和数据一致性
- 检查数据库表结构和数据
- 验证文件状态的一致性
- 分析数据库性能问题

### debug_merge_action.py (从根目录移动)
**用途**: 调试合并动作的执行过程
- 分析合并动作的触发条件
- 验证动作执行的正确性
- 检查动作执行后的状态变化

### debug_replacement.py (从根目录移动)
**用途**: 调试文件替换检测逻辑
- 验证替换检测算法
- 分析替换条件的判断过程
- 检查替换后的数据状态

## 运行方式

```bash
# 从项目根目录运行
cd /path/to/xjj-housekeeper

# 运行具体的调试脚本
python debug/video_info_collector/debug_full_merge.py
python debug/video_info_collector/debug_duplicates.py
python debug/video_info_collector/debug_db_status.py
```

## 注意事项

1. **数据安全**: 这些脚本主要用于读取和分析，不会修改重要数据
2. **环境要求**: 需要在项目根目录运行，确保能正确导入模块
3. **输出解读**: 脚本会输出详细的调试信息，请仔细阅读分析结果
4. **问题反馈**: 如发现调试脚本本身的问题，请及时反馈修复