from __future__ import annotations

from typing import List, Dict


TABLE_STYLE = """
<style>
.sr-table { width:100%; border-collapse: collapse; }
.sr-table th, .sr-table td { border-bottom:1px solid #E5E7EB; padding:8px 10px; font-size:14px; color:#1F2937; }
.sr-table thead th { background:#F3F4F6; text-align:left; }
.sr-table tbody tr:nth-child(odd) { background:#FAFAFA; }
.sr-table tbody tr:hover { background:#f5f8ff; }
.nowrap { white-space: nowrap; }
.breakall { word-break: break-all; }
</style>
"""


def render_table(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return TABLE_STYLE + "<div class=\"empty\">暂无数据</div>"

    headers = ["视频", "大小", "路径"]
    html = [TABLE_STYLE, '<table class=\"sr-table\">']
    html.append("<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>")
    html.append("<tbody>")
    for row in rows:
        html.append(
            "<tr>"
            f"<td class=\"nowrap\">{row.get('视频','')}</td>"
            f"<td class=\"nowrap\">{row.get('大小','')}</td>"
            f"<td class=\"breakall\">{row.get('路径','')}</td>"
            "</tr>"
        )
    html.append("</tbody></table>")
    return "".join(html)


def render_search_results_table(rows: List[Dict[str, str]]) -> str:
    # 将搜索结果的字段映射到表格所需的字段
    mapped_rows = []
    for row in rows:
        mapped_row = {
            '视频': f"{row.get('filename', '')}<br><small>{row.get('duration', '')} | {row.get('resolution', '')}</small>",
            '大小': row.get('file_size', ''),
            '路径': row.get('file_path', '')
        }
        mapped_rows.append(mapped_row)
    
    return render_table(mapped_rows)
