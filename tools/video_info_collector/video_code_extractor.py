#!/usr/bin/env python3
"""
视频编码提取器

从视频文件名中提取业务编码（video_code）的工具模块。
支持多种编码格式和自定义规则。
"""

import re
import os
from typing import Optional, List, Pattern, Dict, Any
from pathlib import Path


class VideoCodeExtractor:
    """视频编码提取器"""
    
    # 默认的编码提取规则（按优先级排序）
    DEFAULT_PATTERNS = [
        # 标准格式：ABC-123, XYZ-456, DEF-789
        r'([A-Z]{2,6}-\d{2,6})',
        
        # 带下划线格式：ABC_123, XYZ_456
        r'([A-Z]{2,6}_\d{2,6})',
        
        # 纯数字编码：123456, 789012（至少4位）
        r'(\d{4,8})',
        
        # 字母数字混合：ABC123, XYZ456
        r'([A-Z]{2,4}\d{2,6})',
        
        # 带点分隔：ABC.123, XYZ.456
        r'([A-Z]{2,6}\.\d{2,6})',
        
        # 复杂格式：ABC-123-HD, XYZ-456-4K
        r'([A-Z]{2,6}-\d{2,6}(?:-[A-Z0-9]{1,4})?)',
    ]
    
    def __init__(self, custom_patterns: Optional[List[str]] = None):
        """
        初始化编码提取器
        
        Args:
            custom_patterns: 自定义正则表达式模式列表
        """
        self.patterns: List[Pattern] = []
        
        # 编译自定义模式（优先级最高）
        if custom_patterns:
            for pattern in custom_patterns:
                try:
                    self.patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    # 忽略无效的正则表达式
                    continue
        
        # 编译默认模式
        for pattern in self.DEFAULT_PATTERNS:
            try:
                self.patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                continue
    
    def extract_code(self, filename: str) -> Optional[str]:
        """
        从文件名中提取视频编码
        
        Args:
            filename: 文件名（可以包含路径）
            
        Returns:
            提取的视频编码，如果未找到返回None
        """
        if not filename:
            return None
        
        # 只使用文件名部分，去除路径和扩展名
        base_name = os.path.splitext(os.path.basename(filename))[0]
        
        # 清理文件名：移除常见的无关字符和标记
        cleaned_name = self._clean_filename(base_name)
        
        # 按优先级尝试每个模式
        for pattern in self.patterns:
            matches = pattern.findall(cleaned_name)
            if matches:
                # 返回第一个匹配的结果，转换为大写
                code = matches[0].upper()
                
                # 验证提取的编码是否合理
                if self._validate_code(code):
                    return code
        
        return None
    
    def extract_codes_batch(self, filenames: List[str]) -> Dict[str, Optional[str]]:
        """
        批量提取视频编码
        
        Args:
            filenames: 文件名列表
            
        Returns:
            文件名到编码的映射字典
        """
        result = {}
        for filename in filenames:
            result[filename] = self.extract_code(filename)
        return result
    
    def _clean_filename(self, filename: str) -> str:
        """
        清理文件名，移除干扰字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除常见的标记和分隔符
        cleaned = filename
        
        # 移除方括号内容：[1080p], [BluRay], [x264]
        cleaned = re.sub(r'\[.*?\]', ' ', cleaned)
        
        # 移除圆括号内容：(2024), (Director's Cut)
        cleaned = re.sub(r'\(.*?\)', ' ', cleaned)
        
        # 移除常见的质量标记
        quality_markers = [
            r'\b(1080p|720p|480p|4K|HD|SD|BluRay|DVDRip|WEBRip|HDTV)\b',
            r'\b(x264|x265|H264|H265|HEVC|AVC)\b',
            r'\b(AAC|AC3|DTS|MP3|FLAC)\b',
            r'\b(PROPER|REPACK|INTERNAL|LIMITED)\b'
        ]
        
        for marker in quality_markers:
            cleaned = re.sub(marker, ' ', cleaned, flags=re.IGNORECASE)
        
        # 标准化空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _validate_code(self, code: str) -> bool:
        """
        验证提取的编码是否合理
        
        Args:
            code: 提取的编码
            
        Returns:
            是否为有效编码
        """
        if not code or len(code) < 3:
            return False
        
        # 排除常见的非编码字符串
        invalid_codes = {
            'DVD', 'BLU', 'RAY', 'WEB', 'RIP', 'CAM', 'TS', 'TC',
            'SCR', 'R5', 'R6', 'HDTV', 'PDTV', 'DSR', 'HDCAM',
            '1080', '720', '480', '2160', 'UHD', '4K', 'HD', 'SD',
            'X264', 'X265', 'H264', 'H265', 'HEVC', 'AVC', 'XVID',
            'AAC', 'AC3', 'DTS', 'MP3', 'FLAC', 'OGG', 'WAV',
            'ENG', 'CHN', 'JPN', 'KOR', 'FRA', 'GER', 'SPA', 'ITA'
        }
        
        if code.upper() in invalid_codes:
            return False
        
        # 排除纯数字且过短的编码
        if code.isdigit() and len(code) < 4:
            return False
        
        # 排除过长的编码
        if len(code) > 20:
            return False
        
        return True
    
    def get_extraction_stats(self, filenames: List[str]) -> Dict[str, Any]:
        """
        获取提取统计信息
        
        Args:
            filenames: 文件名列表
            
        Returns:
            统计信息字典
        """
        results = self.extract_codes_batch(filenames)
        
        total_files = len(filenames)
        extracted_count = sum(1 for code in results.values() if code is not None)
        failed_count = total_files - extracted_count
        
        # 统计编码模式
        code_patterns = {}
        for code in results.values():
            if code:
                # 分析编码模式
                if re.match(r'^[A-Z]+-\d+$', code):
                    pattern_type = 'letter-number'
                elif re.match(r'^[A-Z]+_\d+$', code):
                    pattern_type = 'letter_number'
                elif re.match(r'^\d+$', code):
                    pattern_type = 'pure_number'
                elif re.match(r'^[A-Z]+\d+$', code):
                    pattern_type = 'mixed_alphanumeric'
                else:
                    pattern_type = 'other'
                
                code_patterns[pattern_type] = code_patterns.get(pattern_type, 0) + 1
        
        return {
            'total_files': total_files,
            'extracted_count': extracted_count,
            'failed_count': failed_count,
            'success_rate': extracted_count / total_files if total_files > 0 else 0.0,
            'code_patterns': code_patterns,
            'failed_files': [f for f, code in results.items() if code is None]
        }
    
    def add_custom_pattern(self, pattern: str) -> bool:
        """
        添加自定义提取模式
        
        Args:
            pattern: 正则表达式模式
            
        Returns:
            是否添加成功
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            # 插入到列表开头，给予最高优先级
            self.patterns.insert(0, compiled_pattern)
            return True
        except re.error:
            return False
    
    def test_pattern(self, pattern: str, test_filenames: List[str]) -> Dict[str, Any]:
        """
        测试自定义模式的效果
        
        Args:
            pattern: 要测试的正则表达式模式
            test_filenames: 测试文件名列表
            
        Returns:
            测试结果
        """
        try:
            test_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {'error': f'Invalid regex pattern: {e}'}
        
        results = {}
        for filename in test_filenames:
            base_name = os.path.splitext(os.path.basename(filename))[0]
            cleaned_name = self._clean_filename(base_name)
            
            matches = test_pattern.findall(cleaned_name)
            if matches:
                code = matches[0].upper()
                if self._validate_code(code):
                    results[filename] = code
                else:
                    results[filename] = f'INVALID: {code}'
            else:
                results[filename] = None
        
        success_count = sum(1 for result in results.values() 
                          if result and not str(result).startswith('INVALID:'))
        
        return {
            'pattern': pattern,
            'results': results,
            'success_count': success_count,
            'total_count': len(test_filenames),
            'success_rate': success_count / len(test_filenames) if test_filenames else 0.0
        }


# 全局默认提取器实例
default_extractor = VideoCodeExtractor()


def extract_video_code(filename: str) -> Optional[str]:
    """
    便捷函数：从文件名中提取视频编码
    
    Args:
        filename: 文件名
        
    Returns:
        提取的视频编码
    """
    return default_extractor.extract_code(filename)


def extract_video_codes_batch(filenames: List[str]) -> Dict[str, Optional[str]]:
    """
    便捷函数：批量提取视频编码
    
    Args:
        filenames: 文件名列表
        
    Returns:
        文件名到编码的映射字典
    """
    return default_extractor.extract_codes_batch(filenames)


if __name__ == '__main__':
    # 测试代码
    test_files = [
        'ABC-123.mp4',
        'XYZ-456.mkv',
        'DEF_789.avi',
        'GHI123.mov',
        'JKL.456.wmv',
        'MNO-789-HD.mp4',
        '123456.mp4',
        'invalid_file.mp4',
        '[1080p]PQR-999[x264].mp4',
        'STU-111 (2024) [BluRay].mkv'
    ]
    
    extractor = VideoCodeExtractor()
    
    print("Video Code Extraction Test:")
    print("=" * 50)
    
    for filename in test_files:
        code = extractor.extract_code(filename)
        print(f"{filename:<35} -> {code or 'None'}")
    
    print("\nExtraction Statistics:")
    print("=" * 50)
    stats = extractor.get_extraction_stats(test_files)
    print(f"Total files: {stats['total_files']}")
    print(f"Extracted: {stats['extracted_count']}")
    print(f"Failed: {stats['failed_count']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Code patterns: {stats['code_patterns']}")