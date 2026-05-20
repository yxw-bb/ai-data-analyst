"""FastAPI后端：上传数据 → 自动生成6步分析报告"""
import os
import shutil
import uuid
import pandas as pd
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.llm import get_data_schema, generate_step_code, generate_summary, ANALYSIS_STEPS
from backend.sandbox import execute_code
from backend.database import init_db, save_analysis, get_history

app = FastAPI(title="AI数据洞察报告生成器", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
def startup():
    init_db()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传CSV/Excel"""
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "仅支持CSV和Excel文件")

    file_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix
    save_path = UPLOAD_DIR / f"{file_id}{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    schema = get_data_schema(str(save_path))
    if not schema["columns"]:
        os.unlink(save_path)
        raise HTTPException(400, "无法解析文件")

    return {
        "file_id": file_id,
        "file_name": file.filename,
        "columns": schema["columns"],
        "rows": schema["rows"],
        "sample": schema["sample_data"],
    }


@app.post("/api/generate-report")
async def generate_report(file_id: str = Form(...)):
    """执行6步分析，返回完整报告"""
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(404, "文件不存在")
    file_path = str(matches[0])
    file_name = Path(matches[0]).name

    schema = get_data_schema(file_path)
    if not schema["columns"]:
        raise HTTPException(400, "无法解析数据")

    # 逐步执行分析
    steps_result = []
    all_outputs = ""

    for step in ANALYSIS_STEPS:
        try:
            code = generate_step_code(schema, step)
            result = execute_code(code, file_path)

            if result["error"]:
                # 部分步骤失败不中断
                steps_result.append({
                    "name": step["name"],
                    "icon": step["icon"],
                    "code": code,
                    "output": f"执行出错：{result['error']}",
                    "charts": [],
                    "error": result["error"],
                })
            else:
                steps_result.append({
                    "name": step["name"],
                    "icon": step["icon"],
                    "code": code,
                    "output": result["output"],
                    "charts": result["charts"],
                    "error": None,
                })
                all_outputs += f"\n=== {step['name']} ===\n{result['output']}\n"

        except Exception as e:
            steps_result.append({
                "name": step["name"],
                "icon": step["icon"],
                "code": "",
                "output": f"生成失败：{str(e)}",
                "charts": [],
                "error": str(e),
            })

    # 生成摘要
    summary = generate_summary(file_name, schema, all_outputs)

    # 存入数据库
    analysis_id = save_analysis(
        file_name=file_name,
        question="[自动报告生成]",
        code=str([s["name"] for s in steps_result]),
        output=all_outputs[:500],
        interpretation=summary,
        charts=[],
    )

    return {
        "analysis_id": analysis_id,
        "file_name": file_name,
        "rows": schema["rows"],
        "columns": len(schema["columns"]),
        "summary": summary,
        "steps": steps_result,
    }


@app.get("/api/history")
async def history(limit: int = 20):
    return {"history": get_history(limit)}


@app.get("/")
async def root():
    return {"service": "AI数据洞察报告生成器", "version": "2.0"}
