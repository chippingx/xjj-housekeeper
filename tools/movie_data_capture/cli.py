import argparse
import sys
from typing import List, Optional

from .service import MovieDataCaptureService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="movie-data-capture",
        description="根据视频号查询女演员；根据女演员查询作品清单（含视频号、发布日期）",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--database",
        default=None,
        help="SQLite 数据库路径（默认使用 video_info_collector 的默认数据库）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    by_code = sub.add_parser("by-code", help="根据视频号查询女演员名字")
    by_code.add_argument("video_code", help="视频号，如 CODE-EXAMPLE")
    by_code.add_argument("--force-refresh", action="store_true", help="忽略缓存，强制重新抓取并写入缓存")

    by_actress = sub.add_parser("by-actress", help="根据女演员名字列出作品清单")
    by_actress.add_argument("actress_name", help="女演员名字，如 示例艺人")
    by_actress.add_argument("--force-refresh", action="store_true", help="忽略缓存，强制重新抓取并写入缓存")

    return parser


def _print_actresses(actresses: List[str]) -> None:
    if not actresses:
        print("Actress not found")
        return
    print(", ".join(actresses))


def _print_works(works) -> None:
    if not works:
        print("No works found")
        return
    print(f"{'Video Code':<15} | {'Date':<12} | Title")
    print("-" * 80)
    works_sorted = sorted(
        works,
        key=lambda w: (w.release_date or "", w.video_code),
        reverse=True,
    )
    for w in works_sorted:
        title = (w.title or "").replace("\n", " ").strip()
        print(f"{w.video_code:<15} | {(w.release_date or ''):<12} | {title}")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    svc = MovieDataCaptureService(db_path=args.database)
    try:
        if args.command == "by-code":
            actresses = svc.get_actress_names_by_video_code(args.video_code, force_refresh=args.force_refresh)
            _print_actresses(actresses)
            return 0 if actresses else 1
        if args.command == "by-actress":
            works = svc.get_works_by_actress_name(
                args.actress_name,
                force_refresh=args.force_refresh,
            )
            _print_works(works)
            return 0 if works else 1
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        svc.close()


if __name__ == "__main__":
    sys.exit(main())
