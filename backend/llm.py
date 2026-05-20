"""
LLM编排：自然语言 → 生成分析代码 → 解读结果

Prompt链分为两步：
1. CodeGen：根据数据Schema + 用户问题 → 生成Python代码
2. Interpreter：根据执行结果 → 用自然语言解读
"""
import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

CHAT_MODEL = "deepseek-chat"

CODE_GEN_PROMPT = """你是一个数据分析专家。用户上传了一个CSV文件，请你根据数据结构和用户问题，生成Python代码来完成分析。

## 数据结构
- 列名：{columns}
- 行数：{rows}
- 前5行数据：
{sample_data}

## 用户问题
{question}

## 代码要求
1. 使用变量 `df`（已预加载），不要重新读取文件
2. 只输出Python代码，不要解释，不要markdown代码块标记
3. 使用 `print()` 输出分析结果（描述文字 + 关键数据）
4. 如果需要图表，使用 `plt.figure()` 创建新figure，一个figure一张图
5. 图表要有标题、坐标轴标签（中文）
6. 代码要健壮：处理缺失值、检查数据类型

## 可用的库
pandas (pd), numpy (np), matplotlib.pyplot (plt)

现在请输出代码："""


INTERPRETER_PROMPT = """你是一个数据分析师。请用简洁的中文解读以下分析结果。

用户问题：{question}
代码执行输出：{output}

规则：
1. 2-4句话总结关键发现
2. 有数字就说数字，不要模糊
3. 如果执行出错，解释可能的原因"""


def get_data_schema(file_path: str) -> dict:
    """读取CSV/Excel，提取Schema信息"""
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, encoding="utf-8-sig", nrows=5)
            full_df = pd.read_csv(file_path, encoding="utf-8-sig")
        else:
            df = pd.read_excel(file_path, nrows=5)
            full_df = pd.read_excel(file_path)

        return {
            "columns": list(df.columns),
            "rows": len(full_df),
            "sample_data": df.to_string(),
        }
    except Exception as e:
        return {"columns": [], "rows": 0, "sample_data": f"读取失败：{e}"}


def generate_code(schema: dict, question: str) -> str:
    """根据数据Schema和用户问题，让LLM生成分析代码"""
    prompt = CODE_GEN_PROMPT.format(
        columns=schema["columns"],
        rows=schema["rows"],
        sample_data=schema["sample_data"],
        question=question,
    )

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )

    code = response.choices[0].message.content.strip()

    # 清洗：去掉可能的markdown包裹
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    return code.strip()


def interpret_result(question: str, output: str) -> str:
    """让LLM用自然语言解读分析结果"""
    if not output or not output.strip():
        return "分析完成，请查看图表和输出数据。"
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{
                "role": "user",
                "content": INTERPRETER_PROMPT.format(question=question, output=output),
            }],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"解读生成失败：{e}"
