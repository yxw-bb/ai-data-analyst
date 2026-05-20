"""FastAPI后端：文件上传、分析请求、历史查询"""
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.llm import get_data_schema, generate_code, interpret_result
from backend.sandbox import execute_code
from backend.database import init_db, save_analysis, get_history

app = FastAPI(title="AI数据分析工作台", version="1.0")

# 允许跨域（Streamlit前端调用）
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
    """上传CSV/Excel，返回文件ID和Schema"""
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


@app.post("/api/analyze")
async def analyze(file_id: str = Form(...), question: str = Form(...)):
    """分析数据：生成代码 → 沙箱执行 → 解读结果"""
    # 找到上传的文件
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(404, "文件不存在，请重新上传")
    file_path = str(matches[0])

    # Step 1: 获取数据Schema
    schema = get_data_schema(file_path)
    if not schema["columns"]:
        raise HTTPException(400, "无法解析数据文件")

    # Step 2: LLM生成代码
    code = generate_code(schema, question)

    # Step 3: 沙箱执行
    result = execute_code(code, file_path)

    # Step 4: 解读结果
    interpretation = ""
    if result["output"] and not result["error"]:
        interpretation = interpret_result(question, result["output"])

    # Step 5: 存历史
    analysis_id = save_analysis(
        file_name=matches[0].name,
        question=question,
        code=code,
        output=result["output"],
        interpretation=interpretation,
        charts=result["charts"],
    )

    return {
        "analysis_id": analysis_id,
        "code": code,
        "output": result["output"],
        "charts": result["charts"],
        "interpretation": interpretation,
        "error": result["error"],
    }


@app.get("/api/history")
async def history(limit: int = 20):
    """查询历史分析记录"""
    return {"history": get_history(limit)}


@app.get("/")
async def root():
    return {"service": "AI数据分析工作台", "version": "1.0"}
