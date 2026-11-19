from pathlib import Path
import sqlite3
import time
from pydantic import BaseModel
from core.llm import call_llm_structured

DEFAULT_DB_PATH = Path("db/sandbox.db")


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path) if db_path else DEFAULT_DB_PATH


class AgentTrace(BaseModel):
    question: str
    sql: str
    reasoning: str
    policies_used: list[str]
    result: object
    error: str | None = None
    latency_ms: float


def get_db_schema(db_path: str | Path | None = None) -> str:
    target_db = _resolve_db_path(db_path)
    conn = sqlite3.connect(target_db)
    try:
        cursor = conn.cursor()
        tables = cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        chunks = []
        for name, ddl in tables:
            cols = cursor.execute(f"PRAGMA table_info({name})").fetchall()
            col_summary = ", ".join(f"{c[1]} ({c[2] or 'ANY'})" for c in cols)
            chunks.append(f"Table: {name}\nColumns: {col_summary}\nDDL: {ddl}")
        return "\n\n".join(chunks)
    finally:
        conn.close()


def execute_sql_readonly(
    sql: str,
    db_path: str | Path | None = None,
) -> tuple[object, str | None]:
    cleaned = sql.strip().rstrip(";").strip()
    upper = cleaned.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return None, "Only read-only SELECT/WITH queries are allowed."
    for forbidden in ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "ATTACH ", "PRAGMA "]:
        if forbidden in upper:
            return None, f"Forbidden SQL keyword detected: {forbidden.strip()}"

    target_db = _resolve_db_path(db_path)
    start = time.perf_counter()
    try:
        conn = sqlite3.connect(f"file:{target_db.resolve()}?mode=ro", uri=True)
        try:
            rows = conn.execute(cleaned).fetchall()
            _ = (time.perf_counter() - start) * 1000
            return rows, None
        finally:
            conn.close()
    except Exception as exc:
        return None, str(exc)


def run_agent(
    question: str,
    policies: list[str] | None = None,
    db_path: str | Path | None = None,
) -> AgentTrace:
    start = time.perf_counter()
    schema = get_db_schema(db_path)
    active_policies = [p.content if hasattr(p, "content") else str(p) for p in (policies or [])]
    policy_block = (
        "\n".join(f"- {p}" for p in active_policies)
        if active_policies
        else "None"
    )

    class SqlResponse(BaseModel):
        reasoning: str
        sql: str

    system_prompt = (
        "You are a SQLite Text-to-SQL analyst. Given the database schema and active rules/policies, "
        "write a single valid read-only SQLite SELECT query to answer the question.\n"
        "Follow all applicable policies strictly.\n"
        "Return strict JSON with 'reasoning' and 'sql'."
    )
    user_prompt = (
        f"Database Schema:\n{schema}\n\n"
        f"Active Policies:\n{policy_block}\n\n"
        f"Question: {question}"
    )

    resp = call_llm_structured(system_prompt, user_prompt, SqlResponse)
    rows, err = execute_sql_readonly(resp.sql, db_path=db_path)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    return AgentTrace(
        question=question,
        sql=resp.sql,
        reasoning=resp.reasoning,
        policies_used=active_policies,
        result=rows,
        error=err,
        latency_ms=latency_ms,
    )