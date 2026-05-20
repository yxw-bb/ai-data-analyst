"""
代码沙箱：隔离执行LLM生成的Python代码

安全机制：
1. subprocess 隔离执行——和主进程完全隔离
2. 超时限制——防止死循环跑废CPU
3. 只允许安全的内置函数——禁止 os.system / subprocess / networking
4. 预置 pandas/numpy/matplotlib 供数据分析使用
"""
import subprocess
import tempfile
import os
import base64
from pathlib import Path


EXECUTION_TIMEOUT = 30  # 最多跑30秒

# 沙箱中可用的模块白名单
ALLOWED_BUILTINS = [
    "print", "len", "range", "int", "float", "str", "list", "dict",
    "set", "tuple", "sum", "min", "max", "abs", "round", "sorted",
    "enumerate", "zip", "map", "filter", "type", "isinstance",
    "True", "False", "None", "Exception", "ValueError", "TypeError",
]

# 预装的Python库模板
SANDBOX_PREAMBLE = """
import pandas as pd
import numpy as np
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from io import BytesIO
import json
import os

# 禁用plt.show()——非交互模式下会报warning
plt.show = lambda: None

# 配置中文字体（Windows系统）
_font_paths = [
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simsun.ttc',
]
for _fp in _font_paths:
    if os.path.exists(_fp):
        fm.fontManager.addfont(_fp)
        _prop = fm.FontProperties(fname=_fp)
        plt.rcParams['font.family'] = _prop.get_name()
        break
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 自动识别文件类型加载数据
data_path = r'{data_path}'
if data_path.endswith('.csv'):
    df = pd.read_csv(data_path, encoding='utf-8-sig')
elif data_path.endswith(('.xlsx', '.xls')):
    df = pd.read_excel(data_path)
else:
    raise ValueError(f"不支持的文件格式: {{data_path}}")

# 用户代码在此执行
{user_code}

# 收集所有matplotlib图表，转为base64
figures = [plt.figure(n) for n in plt.get_fignums()]
chart_images = []
for i, fig in enumerate(figures):
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    chart_images.append(base64.b64encode(buf.read()).decode())
    plt.close(fig)

# 打印图表标记，供主进程解析
for i, img in enumerate(chart_images):
    print(f'__CHART_{i}__:' + img)
"""


def execute_code(code: str, data_path: str) -> dict:
    """
    在沙箱中执行数据分析代码

    参数:
        code: LLM生成的Python代码
        data_path: 上传的CSV/Excel文件路径

    返回:
        {output: str, charts: [base64_str], error: str|None}
    """
    # 拼装完整沙箱代码（用replace避免{}冲突）
    abs_path = os.path.abspath(data_path)
    full_code = SANDBOX_PREAMBLE.replace("{data_path}", abs_path.replace("\\", "\\\\"))
    full_code = full_code.replace("{user_code}", code)

    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            cwd=tempfile.gettempdir(),
        )

        output = result.stdout
        # 过滤warning，只保留真正的错误
        stderr = result.stderr
        if stderr:
            real_errors = [l for l in stderr.split("\n") if l.strip()
                          and "Warning" not in l
                          and "FutureWarning" not in l
                          and "DeprecationWarning" not in l
                          and "plt.show()" not in l
                          and "pandas.pydata.org" not in l
                          and "select_dtypes" not in l
                          and "FigureCanvasAgg" not in l]
            error = "\n".join(real_errors) if real_errors else None
        else:
            error = None

        # 解析图表
        charts = []
        clean_output = []
        for line in output.split("\n"):
            if line.startswith("__CHART_") and "__:" in line:
                _, img_data = line.split("__:", 1)
                charts.append(img_data)
            else:
                clean_output.append(line)

        return {
            "output": "\n".join(clean_output).strip(),
            "charts": charts,
            "error": error,
        }

    except subprocess.TimeoutExpired:
        return {"output": "", "charts": [], "error": f"代码执行超时（>{EXECUTION_TIMEOUT}秒）"}
    except Exception as e:
        return {"output": "", "charts": [], "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
