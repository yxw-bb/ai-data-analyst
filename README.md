# AI数据分析工作台

基于LLM的智能数据分析平台。用户上传CSV/Excel并通过自然语言描述分析需求，系统自动生成Python代码、沙箱执行、可视化渲染并输出解读报告。

## 功能

- **自然语言驱动**：用中文描述分析需求，无需写代码
- **代码自动生成**：LLM根据数据Schema生成pandas/matplotlib分析代码
- **安全沙箱执行**：subprocess隔离执行，30秒超时保护
- **图表自动渲染**：matplotlib生成图表，中文字体支持
- **AI结果解读**：对执行结果进行自然语言总结
- **历史记录**：SQLite持久化所有分析过程

## 架构

```
Streamlit前端 ←→ FastAPI后端
                    ├── LLM编排（DeepSeek API）
                    ├── 代码沙箱（subprocess隔离）
                    └── SQLite（分析历史）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key

创建 `.env` 文件，填入DeepSeek API Key。

### 3. 启动后端

```bash
uvicorn backend.main:app --port 8000
```

### 4. 启动前端

```bash
streamlit run frontend/app.py
```

打开 http://localhost:8501 ，上传数据开始分析。

## 项目结构

```
ai-data-analyst/
├── backend/
│   ├── main.py       # FastAPI应用
│   ├── llm.py         # LLM编排（代码生成+解读）
│   ├── sandbox.py     # 代码沙箱执行
│   └── database.py    # SQLite数据库
├── frontend/
│   └── app.py         # Streamlit界面
└── requirements.txt
```

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | DeepSeek Chat API |
| 后端 | FastAPI + uvicorn |
| 前端 | Streamlit |
| 数据库 | SQLite |
| 数据分析 | pandas + numpy + matplotlib |
| 沙箱 | subprocess（进程隔离+超时） |

## License

MIT
