from __future__ import annotations

import re
from typing import Tuple

VIDEO_CODE_REGEX = re.compile(r"^[A-Z]{3,6}-\d{3,4}$", re.IGNORECASE)


def is_valid_video_code(text: str) -> bool:
    if text is None:
        return False
    stripped = text.strip()
    if stripped == "":
        return False
    if "*" in stripped or "?" in stripped:
        return False
    return VIDEO_CODE_REGEX.match(stripped) is not None


def validate_query_input(text: str) -> Tuple[bool, str]:
    from .app import QUERY_EMPTY_HINT, QUERY_INVALID_HINT  # 局部导入避免循环依赖问题

    if text is None or text.strip() == "":
        return False, QUERY_EMPTY_HINT
    
    stripped = text.strip()
    
    # 检查是否为空或包含通配符
    if "*" in stripped or "?" in stripped:
        return False, QUERY_INVALID_HINT
    
    # 如果是标准视频编号格式，允许查询
    if is_valid_video_code(stripped):
        return True, ""
    
    # 如果不是标准格式但长度合理（至少2个字符），也允许查询
    if len(stripped) >= 2:
        return True, "将搜索包含关键词的视频文件"
    
    # 其他情况不允许
    return False, QUERY_INVALID_HINT
