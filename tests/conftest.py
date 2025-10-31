import os
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保测试可以导入顶层包（如 tools.filename_formatter）
ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)