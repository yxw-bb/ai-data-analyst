"""SQLite数据库：存分析历史记录"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            question TEXT NOT NULL,
            generated_code TEXT,
            output_text TEXT,
            interpretation TEXT,
            charts_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_analysis(file_name: str, question: str, code: str,
                  output: str, interpretation: str, charts: list) -> int:
    import json
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO analysis_history
           (file_name, question, generated_code, output_text, interpretation, charts_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (file_name, question, code, output, interpretation, json.dumps(charts)),
    )
    conn.commit()
    analysis_id = cur.lastrowid
    conn.close()
    return analysis_id


def get_history(limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
