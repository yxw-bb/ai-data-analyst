"""Streamlit前端：上传数据 → 一键生成6步分析报告"""
import base64
import io

import requests
import streamlit as st
from PIL import Image

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI数据洞察报告生成器", layout="wide")
st.title("📊 AI数据洞察报告生成器")
st.caption("上传CSV/Excel → 一键生成6步完整分析报告（概览 + 统计 + 相关性 + 趋势 + 对比 + 建议）")

# ---- 侧边栏 ----
with st.sidebar:
    st.header("📁 上传数据")
    uploaded_file = st.file_uploader("选择CSV或Excel文件", type=["csv", "xlsx", "xls"])

    if uploaded_file and st.button("上传", use_container_width=True):
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
                }
                st.success(f"{data['rows']}行 × {len(data['columns'])}列")
            else:
                st.error("上传失败")

    if "schema" in st.session_state:
        s = st.session_state["schema"]
        st.info(f"📋 {st.session_state['file_name']}\n\n{s['rows']}行 × {len(s['columns'])}列\n\n列名：{'、'.join(s['columns'][:8])}")

    st.divider()

    if "file_id" in st.session_state:
        if st.button("🚀 生成分析报告", type="primary", use_container_width=True):
            with st.spinner("AI正在自动分析（6个步骤，约需1-2分钟）..."):
                resp = requests.post(
                    f"{API_URL}/api/generate-report",
                    data={"file_id": st.session_state["file_id"]},
                    timeout=180,
                )
                if resp.status_code == 200:
                    st.session_state["report"] = resp.json()
                    st.success("报告生成完成！")
                else:
                    st.error(resp.json().get("detail", "生成失败"))

# ---- 主区域：展示报告 ----
report = st.session_state.get("report")
if report:
    # 摘要
    st.header("📝 分析摘要")
    st.info(report["summary"])

    # 6步结果
    st.header("📊 详细分析（6步）")

    for i, step in enumerate(report["steps"]):
        with st.expander(f"{step['icon']} 第{i+1}步：{step['name']}", expanded=(i == 0)):
            col1, col2 = st.columns([3, 2])

            with col1:
                if step.get("output"):
                    st.text_area("输出", step["output"], height=150, key=f"out_{i}")

                if step.get("error"):
                    st.warning(f"⚠️ {step['error']}")

            with col2:
                if step.get("charts"):
                    for j, chart_b64 in enumerate(step["charts"]):
                        try:
                            img = Image.open(io.BytesIO(base64.b64decode(chart_b64)))
                            st.image(img, use_container_width=True)
                        except Exception:
                            pass

            if step.get("code"):
                st.caption(f"生成代码 ({len(step['code'])}字符)")
                st.code(step["code"], language="python")

elif "file_id" not in st.session_state:
    st.info("👈 请先在左侧上传数据文件")
else:
    st.info("👈 点击「生成分析报告」按钮开始自动分析")
