from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":  # 兼容 Streamlit 直接运行
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

import streamlit as st

from ui.validation import validate_query_input
from ui.maintain_form import render_mobile_density_styles
from ui.table_renderer import render_search_results_table
from ui.services import search_videos, start_maintain

# 路由常量（与 design_system.md 顶部入口文案一致）
ROUTE_QUERY = "query"
ROUTE_MAINTAIN = "maintain"

PILL_LABEL_QUERY = "维护视频数据"  # 查询页显示的入口文案
PILL_LABEL_MAINTAIN = "返回查询"   # 维护页显示的入口文案

# 查询输入与提示常量（与设计一致）
QUERY_PLACEHOLDER = "按视频编号精确查询（示例：ABC-123）"
QUERY_EMPTY_HINT = "请输入关键词进行查询"
QUERY_INVALID_HINT = "仅精确匹配；禁空/禁模糊"


def get_top_pill_label(route: str) -> str:
    return PILL_LABEL_MAINTAIN if route == ROUTE_MAINTAIN else PILL_LABEL_QUERY


def route_after_toggle(route: str) -> str:
    return ROUTE_QUERY if route == ROUTE_MAINTAIN else ROUTE_MAINTAIN


def route_after_escape(route: str, modal_open: bool) -> str:
    # 当完成弹框打开时，Esc 应返回查询页
    if modal_open:
        return ROUTE_QUERY
    return route


def _init_session_state() -> None:
    # 检查URL参数中的路由
    query_params = st.query_params
    if "route" in query_params:
        route_from_url = query_params["route"]
        if route_from_url in [ROUTE_QUERY, ROUTE_MAINTAIN]:
            st.session_state["route"] = route_from_url
    
    if "route" not in st.session_state:
        st.session_state["route"] = ROUTE_QUERY
    st.session_state.setdefault("query", "")
    st.session_state.setdefault("query_submit", False)


def _render_topbar() -> None:
    st.markdown(
        """
        <style>
        body { background: #F7F9FC; }
        .topbar { height: 48px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #E5E7EB; padding: 0 16px; }
        .brand { font-weight: 600; color: #1F2937; }
        .pill { border:1px solid #E5E7EB; border-radius:999px; padding:6px 12px; background:#fff; color:#1F2937; cursor:pointer; display:inline-block; }
        </style>
        <div class="topbar"><div class="brand">XJJ</div><div id="pill-slot"></div></div>
        """,
        unsafe_allow_html=True,
    )





def render_query_page() -> None:
    _render_topbar()
    st.title("查询")
    # 顶部入口 pill：查询页文案为"维护视频数据"
    st.button(get_top_pill_label(ROUTE_QUERY), key="to_maintain", on_click=lambda: st.session_state.update({"route": route_after_toggle(ROUTE_QUERY)}))

    # 查询输入区：自动聚焦、占位、支持回车查询
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            label="",
            key="query",
            placeholder=QUERY_PLACEHOLDER,
            label_visibility="collapsed",
        )
    
    with col2:
        do_search = st.button("查询", type="primary")
    
    # 检查回车提交：如果输入框内容变化且不为空，自动触发查询
    if "previous_query" not in st.session_state:
        st.session_state.previous_query = ""
    
    current_query = query.strip()
    if current_query != st.session_state.previous_query:
        if current_query:  # 只有非空内容才触发查询
            do_search = True
        st.session_state.previous_query = current_query

    # 空态：不展示表格
    if not do_search:
        if not query.strip():
            st.info(QUERY_EMPTY_HINT)
        else:
            st.info("🔍 点击查询按钮进行搜索")
        return

    # 查询时验证输入
    keyword = query.strip()
    ok, msg = validate_query_input(keyword)
    
    if not ok:
        st.error(f"❌ {msg}")
        return
    
    # 通过 services 占位进行查询，并以表格策略渲染
    
    # 显示搜索关键词（调试信息）
    st.info(f"🔍 搜索关键词: '{keyword}'")
    
    rows = []
    try:
        rows = search_videos(keyword)
        st.success(f"✅ 找到 {len(rows)} 条结果")
    except Exception as e:  # 最小占位错误处理
        st.error(f"❌ 查询失败：{e}")
        rows = []

    if rows:
        table_html = render_search_results_table(rows)
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("📝 没有找到匹配的视频文件")


def render_maintain_page() -> None:
    _render_topbar()
    st.title("维护")
    # 顶部入口 pill：维护页文案为"返回查询"
    st.button(get_top_pill_label(ROUTE_MAINTAIN), key="to_query", on_click=lambda: st.session_state.update({"route": route_after_toggle(ROUTE_MAINTAIN)}))

    # 移动端紧凑密度样式 + 表单结构
    st.markdown(render_mobile_density_styles(), unsafe_allow_html=True)
    
    # 处理表单提交
    if "maintain_submitted" not in st.session_state:
        st.session_state.maintain_submitted = False
    
    if st.session_state.maintain_submitted:
        # 显示处理结果
        if "maintain_result" in st.session_state:
            result = st.session_state.maintain_result
            if result["success"]:
                st.success(f"✓ {result['message']}")
            else:
                st.error(f"✗ {result['message']}")
        
        # 重置状态
        if st.button("返回"):
            st.session_state.maintain_submitted = False
            if "maintain_result" in st.session_state:
                del st.session_state.maintain_result
            st.rerun()
    else:
        # 根据CSDN文档建议，使用Session State缓存 + tkinter的方式
        # 初始化session state
        if 'selected_scan_path' not in st.session_state:
            st.session_state.selected_scan_path = ""
        if 'show_folder_dialog' not in st.session_state:
            st.session_state.show_folder_dialog = False
        
        # 显示区域
        col1, col2 = st.columns([3, 1])
        
        with col1:
            current_path = st.session_state.selected_scan_path
            if current_path:
                st.success(f"✓ 已选择目录: {current_path}")
            else:
                st.info("💡 点击右侧按钮选择扫描目录")
        
        with col2:
            # 按钮点击时设置标志
            if st.button("📁 选择目录", type="secondary", key="select_dir_button"):
                st.session_state.show_folder_dialog = True
        
        # 如果需要显示对话框，使用subprocess避免线程问题
        if st.session_state.show_folder_dialog:
            try:
                import subprocess
                import tempfile
                import os
                
                # 创建临时文件存储选择的路径
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                # 使用Python脚本在独立进程中运行tkinter
                script_content = f'''
import tkinter as tk
from tkinter import filedialog
import sys

try:
    root = tk.Tk()
    root.withdraw()
    
    try:
        root.attributes('-topmost', True)
    except:
        pass
    
    folder = filedialog.askdirectory(title="选择扫描目录")
    root.destroy()
    
    # 将结果写入临时文件
    with open("{tmp_path}", "w") as f:
        f.write(folder if folder else "")
        
    sys.exit(0)
    
except Exception as e:
    with open("{tmp_path}", "w") as f:
        f.write("")
    sys.exit(1)
'''
                
                # 执行脚本
                result = subprocess.run(
                    [sys.executable, '-c', script_content],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # 读取结果
                try:
                    with open(tmp_path, 'r') as f:
                        folder = f.read().strip()
                except:
                    folder = ""
                
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                # 重置标志
                st.session_state.show_folder_dialog = False
                
                if folder:
                    st.session_state.selected_scan_path = folder
                    st.rerun()
                    
            except Exception as e:
                st.session_state.show_folder_dialog = False
                st.error(f"目录选择失败: {str(e)}")
                
                # 保存结果
                if folder:
                    st.session_state.selected_scan_path = folder
                    st.rerun()
                    
            except Exception as e:
                st.session_state.show_folder_dialog = False
                st.error(f"❌ 打开文件对话框失败: {e}")
                st.info("💡 提示：请手动在下方输入框中输入完整路径")
        
        # Streamlit表单
        with st.form("maintain_form", clear_on_submit=False):
            # 使用选择的路径作为默认值
            scan_path = st.text_input(
                "扫描目录路径", 
                value=st.session_state.selected_scan_path,
                placeholder="点击上方'选择目录'按钮选择路径，或手动输入完整路径", 
                key="scan_path_input"
            )
            tags = st.text_input("标签（可选）", placeholder="标签（可选），例如：电影, 高清", key="tags_input")
            logical_path = st.text_input("逻辑路径（可选）", placeholder="逻辑路径（可选），例如：媒体库/电影/2024", key="logical_path_input")
            
            submitted = st.form_submit_button("开始维护", type="primary")
            
            if submitted:
                if not scan_path or not scan_path.strip():
                    st.error("请提供扫描目录路径")
                else:
                    # 调用服务函数进行维护
                    with st.spinner("正在维护数据，请稍候..."):
                        result = start_maintain(scan_path.strip(), tags, logical_path)
                    st.session_state.maintain_result = result
                    st.session_state.maintain_submitted = True
                    st.rerun()


def main() -> None:
    _init_session_state()
    route = st.session_state.get("route", ROUTE_QUERY)
    if route == ROUTE_QUERY:
        render_query_page()
    elif route == ROUTE_MAINTAIN:
        render_maintain_page()
    else:
        # 回退到查询页
        st.session_state["route"] = ROUTE_QUERY
        render_query_page()


if __name__ == "__main__":
    main()
