import streamlit as st

def validate_search_input(input_str):
    """验证查询输入是否有效"""
    return input_str.strip() != ""

def get_table_columns():
    """获取表格列配置"""
    return ["视频", "大小", "路径", "标签", "逻辑路径"]

def get_navigation_text(page):
    """获取导航文案"""
    if page == "查询":
        return "维护视频数据"
    elif page == "维护":
        return "返回查询"
    return ""

def get_maintain_form_fields():
    """获取维护表单字段"""
    return ["扫描目录", "标签", "逻辑路径"]

def get_progress_states():
    """获取进度状态"""
    return ["等待中", "处理中", "已完成", "失败"]

def main():
    """UI主入口"""
    # 页面配置
    st.set_page_config(
        page_title="视频文件管理系统",
        page_icon="📁",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 顶部导航
    st.markdown("# 视频文件管理系统")
    
    # 页面路由
    page = st.sidebar.selectbox("选择页面", ["查询", "维护"])
    
    # 显示当前页面的导航入口
    st.markdown(f"### {get_navigation_text(page)}")
    
    if page == "查询":
        show_query_page()
    elif page == "维护":
        show_maintain_page()

def show_query_page():
    """显示查询页面"""
    st.subheader("查询视频数据")
    
    # 查询输入框
    search_input = st.text_input("请输入关键词", placeholder="支持精确匹配视频文件名或路径")
    
    # 查询按钮
    search_button = st.button("查询", disabled=not search_input.strip())
    
    # 空态提示
    if not search_input.strip():
        st.info("请输入关键词进行查询")
    
    # 结果表格（空表格）
    if search_button:
        st.dataframe(
            data=[],
            columns=get_table_columns(),
            use_container_width=True,
            hide_index=True
        )

def show_maintain_page():
    """显示维护页面"""
    st.subheader("维护视频数据")
    
    # 维护表单
    with st.form("maintain_form"):
        # 扫描目录
        scan_dir = st.text_input("扫描目录", placeholder="请输入或选择要扫描的目录")
        browse_button = st.button("选择目录", type="secondary")
        
        # 标签
        tag = st.text_input("标签", placeholder="请输入标签")
        
        # 逻辑路径
        logical_path = st.text_input("逻辑路径", placeholder="请输入逻辑路径")
        
        # 开始维护按钮
        maintain_button = st.form_submit_button("开始维护")

if __name__ == "__main__":
    main()