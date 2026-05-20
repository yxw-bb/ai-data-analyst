"""Streamlit前端：上传数据 → 自然语言提问 → 查看分析结果"""
import base64
import io

import requests
import streamlit as st
from PIL import Image

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI数据分析工作台", layout="wide")
st.title("AI数据分析工作台")
st.caption("上传CSV/Excel → 用自然语言描述分析需求 → AI自动生成代码并执行")

# ---- 侧边栏 ----
with st.sidebar:
    st.header("📁 数据上传")

    uploaded_file = st.file_uploader("选择CSV或Excel文件", type=["csv", "xlsx", "xls"])

    file_id = st.session_state.get("file_id")
    schema = st.session_state.get("schema")

    if uploaded_file and st.button("上传数据"):
        with st.spinner("解析数据..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            resp = requests.post(f"{API_URL}/api/upload", files=files)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["file_id"] = data["file_id"]
                st.session_state["file_name"] = data["file_name"]
                st.session_state["schema"] = {
                    "columns": data["columns"],
                    "rows": data["rows"],
                    "sample": data["sample"],
                }
                st.success(f"上传成功：{data['rows']}行，{len(data['columns'])}列")
            else:
                st.error(resp.json().get("detail", "上传失败"))

    if "file_id" in st.session_state:
        st.info(f"当前文件：{st.session_state.get('file_name', '')}")
        if schema:
            st.caption(f"列：{'、'.join(schema['columns'][:8])} | 共{schema['rows']}行")

    st.divider()
    st.header("📋 分析历史")
    if st.button("刷新历史"):
        try:
            resp = requests.get(f"{API_URL}/api/history", params={"limit": 10})
            if resp.status_code == 200:
                history = resp.json()["history"]
                for h in history:
                    with st.expander(f"{h['question'][:40]}... ({h['created_at'][:10]})"):
                        st.caption(h["interpretation"])
        except Exception:
            pass

# ---- 主区域 ----
col1, col2 = st.columns([3, 2])

with col1:
    st.header("💬 分析需求")
    question = st.text_area(
        "用自然语言描述你想做什么分析",
        placeholder="例如：\n- 统计各地区的销售额总和\n- 画出年龄分布的直方图\n- 分析价格和销量之间的相关性\n- 哪个月份的订单量最高？",
        height=120,
    )

    if st.button("开始分析", type="primary", use_container_width=True):
        if not st.session_state.get("file_id"):
            st.error("请先在左侧上传数据文件")
        elif not question.strip():
            st.warning("请输入分析需求")
        else:
            with st.spinner("AI正在分析..."):
                resp = requests.post(
                    f"{API_URL}/api/analyze",
                    data={
                        "file_id": st.session_state["file_id"],
                        "question": question,
                    },
                )

                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state["last_result"] = result
                else:
                    st.error(resp.json().get("detail", "分析失败"))

with col2:
    st.header("📊 分析结果")

    result = st.session_state.get("last_result")
    if result:
        if result.get("error"):
            st.error(f"执行出错：{result['error']}")
        else:
            if result.get("interpretation"):
                st.markdown("### 解读")
                st.success(result["interpretation"])

            if result.get("output"):
                with st.expander("📝 原始输出"):
                    st.code(result["output"], language="text")

            if result.get("charts"):
                st.markdown("### 图表")
                for i, chart_b64 in enumerate(result["charts"]):
                    try:
                        img = Image.open(io.BytesIO(base64.b64decode(chart_b64)))
                        st.image(img, use_container_width=True)
                    except Exception:
                        pass

            if result.get("code"):
                with st.expander("🐍 查看生成的代码"):
                    st.code(result["code"], language="python")

# ---- 底部：历史详情 ----
if st.session_state.get("last_result") and st.session_state.get("last_result", {}).get("interpretation"):
    st.divider()
    st.caption(f"分析ID：{st.session_state['last_result'].get('analysis_id', '')}")
