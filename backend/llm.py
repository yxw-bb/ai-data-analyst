"""
LLM编排：自动生成6步数据分析报告

流程：
1. 数据概览 → 2. 描述统计 → 3. 相关性分析
→ 4. 趋势发现 → 5. 分组对比 → 6. 结论与建议

每步独立生成代码 → 沙箱执行 → 汇总成完整报告
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

# 6个分析步骤的定义
ANALYSIS_STEPS = [
    {
        "name": "数据概览",
        "icon": "📋",
        "prompt": """请生成Python代码，对数据做基本概览：
1. 打印数据形状（行数×列数）
2. 打印所有列名和数据类型
3. 统计每列的缺失值数量和比例
4. 打印数据内存占用

要求：只用print输出，不画图。df已预加载。""",
    },
    {
        "name": "描述统计",
        "icon": "📊",
        "prompt": """请生成Python代码，对数值列做描述统计，并画分布图：
1. 打印数值列的：均值、中位数、标准差、最小值、最大值
2. 为每个数值列画直方图（hist），用plt.figure()创建
3. 画一个箱线图（boxplot）展示所有数值列的分布

要求：每个图表单独一个plt.figure()。df已预加载。""",
    },
    {
        "name": "相关性分析",
        "icon": "🔥",
        "prompt": """请生成Python代码，分析数值列之间的相关性：
1. 打印相关系数矩阵
2. 画热力图（用plt.imshow或plt.matshow），标注相关系数值
3. 找出并打印相关性最高的3对变量

要求：df已预加载。用plt.figure()创建图表。""",
    },
    {
        "name": "趋势发现",
        "icon": "📈",
        "prompt": """请生成Python代码，发现数据中的趋势：
1. 找数据中可能是日期/时间的列，如果有，按时间排序后画折线图
2. 如果没有日期列，对数值列画滚动均值趋势
3. 打印发现的明显趋势或模式

要求：有日期列优先用日期列做趋势。df已预加载。""",
    },
    {
        "name": "分组对比",
        "icon": "📉",
        "prompt": """请生成Python代码，做分组对比分析：
1. 找数据中的分类列（字符串/类别型），选最重要的1-2个
2. 按分类列分组，计算数值列的汇总统计（总和或均值）
3. 画分组柱状图对比
4. 打印Top-3和Bottom-3的分组值

要求：没有分类列就跳过，在print里说明。df已预加载。""",
    },
    {
        "name": "结论与建议",
        "icon": "💡",
        "prompt": """请生成Python代码，汇总前面分析的关键发现：
1. 打印数据质量总结（缺失情况、异常情况）
2. 打印3-5个关键统计结论（带具体数字）
3. 如果有明显的趋势或差异，强调出来

只用print输出，不画图。df已预加载。""",
    },
]

SUMMARY_PROMPT = """你是一位资深数据分析师。请根据以下分析结果，写一份200-300字的数据分析摘要。

数据文件：{file_name}
数据规模：{rows}行 × {cols}列
列名：{columns}

各步骤分析结果：
{all_outputs}

请写一份简洁的分析摘要，包含：
1. 数据整体情况（1-2句）
2. 最关键的2-3个发现（带数字）
3. 1条可执行的建议
"""


def get_data_schema(file_path: str) -> dict:
    """读取CSV/Excel，提取Schema信息"""
    try:
        if file_path.endswith(".csv"):
            full_df = pd.read_csv(file_path, encoding="utf-8-sig")
        else:
            full_df = pd.read_excel(file_path)

        return {
            "columns": list(full_df.columns),
            "rows": len(full_df),
            "sample_data": full_df.head(5).to_string(),
        }
    except Exception as e:
        return {"columns": [], "rows": 0, "sample_data": f"读取失败：{e}"}


def generate_step_code(schema: dict, step: dict) -> str:
    """为单个分析步骤生成代码"""
    prompt = f"""## 数据结构
列名：{schema['columns']}
行数：{schema['rows']}
前5行：
{schema['sample_data']}

## 任务
{step['prompt']}

## 输出规则
只输出Python代码，不要markdown包裹，不要解释。"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )
    code = response.choices[0].message.content.strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:-1])
    return code


def generate_summary(file_name: str, schema: dict, all_outputs: str) -> str:
    """生成分析摘要"""
    if not all_outputs.strip():
        return "无法生成摘要：分析未产生有效输出。"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(
                file_name=file_name,
                rows=schema["rows"],
                cols=len(schema["columns"]),
                columns=", ".join(schema["columns"]),
                all_outputs=all_outputs[:4000],  # 截断避免超token
            ),
        }],
        temperature=0.3,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()
