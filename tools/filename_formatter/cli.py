import argparse
import os
import sys
from typing import List

from dotenv import load_dotenv

from .formatter import FilenameFormatter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filename-formatter",
        description="批量规范化/重命名视频文件名的命令行工具（默认扁平化输出到根目录，递归处理子目录，按配置处理扩展名）",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("directory", help="要处理的目录路径")
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：显示将要执行的操作，但不实际修改文件"
    )
    
    parser.add_argument(
        "--conflict-resolution",
        choices=["skip", "rename"],
        default="skip",
        help="同名文件冲突处理方式: skip(跳过), rename(自动重命名)"
    )
    
    parser.add_argument(
        "--log-operations",
        action="store_true",
        help="记录所有操作到轻量级日志文件"
    )
    parser.add_argument(
        "--verify-size",
        action="store_true",
        help="验证文件大小（轻量级验证）"
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="filename-formatter 0.1.0"
    )
    return parser


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_dotenv()
    # 由配置控制扩展名与最小大小
    # 默认优先环境变量 RENAME_RULES_PATH；未设置则工具内部回退到默认规则文件
    fmt = FilenameFormatter(default_rules_path=None)

    try:
        results = fmt.rename_in_directory(
            args.directory,
            include_subdirs=True,  # 默认递归处理子目录
            flatten_output=True,  # 默认扁平化输出
            dry_run=args.dry_run,
            conflict_resolution=args.conflict_resolution,
            log_operations=args.log_operations,
            verify_size=args.verify_size
        )

        # 简洁输出
        total = len(results)
        successes = sum(1 for r in results if r.status.startswith("success"))
        skipped_exists = sum(1 for r in results if r.status == "skipped: target exists")
        skipped_same = sum(1 for r in results if r.status == "skipped: same name")
        errors = [r for r in results if r.status.startswith("error")]

        print(f"处理目录: {args.directory}")
        print(f"处理扩展名: {', '.join(fmt.video_extensions)}")
        print(f"最小文件大小: {fmt.min_file_size} 字节")
        print(f"使用规则文件: {fmt.get_config_file_path()}")
        print(f"递归子目录: 是\n")

        # 区分预览模式和实际执行的输出
        if args.dry_run:
            print("🔍 预览模式 - 以下是将要执行的操作：")
            print("=" * 50)
        
        for r in results:
             if r.status.startswith("success"):
                 status_info = ""
                 if "(size verified)" in r.status:
                     status_info += " [大小已验证]"
                 print(f"success: {r.original} -> {r.new}{status_info}")
             elif r.status == "preview: would rename":
                 print(f"preview: {r.original} -> {r.new}")
             elif r.status.startswith("skipped"):
                 print(f"skipped: {r.status.split(': ', 1)[1]}: {r.original} -> {r.new}")
             else:
                 print(f"error: {r.original} -> {r.new} ({r.status})")

        print("\n统计:")
        print(f"- 总计: {total}")
        if args.dry_run:
            normal_renames = len([r for r in results if r.status == 'preview: would rename'])
            print(f"- 将要重命名: {normal_renames}")
        else:
            print(f"- 成功: {successes}")
        print(f"- 跳过(目标已存在): {skipped_exists}")
        print(f"- 跳过(同名): {skipped_same}")
        print(f"- 失败: {len(errors)}")
        
        if args.dry_run:
            print("\n💡 这只是预览！要实际执行操作，请移除 --dry-run 参数")

        return 0 if not errors else 1
    except FileNotFoundError:
        print(f"目录不存在: {args.directory}")
        return 2
    except NotADirectoryError:
        print(f"路径不是目录: {args.directory}")
        return 2
    except KeyboardInterrupt:
        print("已取消。")
        return 130
    except Exception as e:
        print(f"执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())