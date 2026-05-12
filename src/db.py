"""
数据库模块 — SQLite 连接 + 模板查询 + 安全审核通道
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from .config import config
from .audit import audit
from .logger import get_logger

_log = get_logger("db")


def _db_path() -> str:
    return config.db_path


@contextmanager
def _connect(readonly: bool = True):
    uri = f"file:{_db_path()}"
    if readonly:
        uri += "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _query(sql: str, params: tuple = (), readonly: bool = True) -> list[dict]:
    """内部查询执行器"""
    with _connect(readonly) as conn:
        cur = conn.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        return rows


def _wrap(data: Any, source: str) -> str:
    """统一返回值格式：{data, _source}"""
    return json.dumps({"data": data, "_source": source}, ensure_ascii=False, default=str)


def _now() -> str:
    """当前时间戳字符串"""
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════
# 模板查询函数（不返回 manager_id）
# ═══════════════════════════════════════════

def get_employee(name: str) -> str:
    t0 = time.time()
    rows = _query(
        "SELECT employee_id, name, department, level, hire_date, email, status "
        "FROM employees WHERE name = ? AND status = 'active'",
        (name,),
    )
    if not rows:
        rows = _query(
            "SELECT employee_id, name, department, level, hire_date, email, status "
            "FROM employees WHERE employee_id = ?",
            (name,),
        )
    _log.info("get_employee(%s) -> %d rows (%.1fms)", name, len(rows), (time.time()-t0)*1000)
    return _wrap(rows, f"employees 表 (模板: employee-info, {_now()})")


def get_employee_projects(name: str) -> str:
    t0 = time.time()
    rows = _query(
        "SELECT p.project_id, p.name, pm.role, p.status "
        "FROM project_members pm "
        "JOIN projects p ON pm.project_id = p.project_id "
        "JOIN employees e ON pm.employee_id = e.employee_id "
        "WHERE e.name = ?",
        (name,),
    )
    _log.info("get_employee_projects(%s) -> %d rows (%.1fms)", name, len(rows), (time.time()-t0)*1000)
    return _wrap(rows, f"project_members + projects 表 (模板: employee-projects, {_now()})")


def get_department_count(dept: str) -> str:
    rows = _query(
        "SELECT COUNT(*) AS count FROM employees "
        "WHERE department = ? AND status = 'active'",
        (dept,),
    )
    _log.info("get_department_count(%s) -> %s", dept, rows[0]["count"] if rows else 0)
    return _wrap(rows, f"employees 表 (模板: department-count, {_now()})")


def get_department_employees(dept: str) -> str:
    rows = _query(
        "SELECT employee_id, name, level, hire_date "
        "FROM employees WHERE department = ? AND status = 'active'",
        (dept,),
    )
    _log.info("get_department_employees(%s) -> %d rows", dept, len(rows))
    return _wrap(rows, f"employees 表 (模板: department-employees, {_now()})")


def get_monthly_attendance(name: str, month: str) -> str:
    rows = _query(
        "SELECT status, COUNT(*) AS count FROM attendance "
        "WHERE employee_id = (SELECT employee_id FROM employees WHERE name = ?) "
        "AND date LIKE ? "
        "GROUP BY status",
        (name, f"{month}-%"),
    )
    _log.info("get_monthly_attendance(%s, %s) -> %d rows", name, month, len(rows))
    return _wrap(rows, f"attendance 表 (模板: monthly-attendance, {_now()})")


def get_employee_kpi(name: str, year: int) -> str:
    rows = _query(
        "SELECT year, quarter, kpi_score, grade "
        "FROM performance_reviews "
        "WHERE employee_id = (SELECT employee_id FROM employees WHERE name = ?) "
        "AND year = ? "
        "ORDER BY quarter",
        (name, year),
    )
    _log.info("get_employee_kpi(%s, %d) -> %d rows", name, year, len(rows))
    return _wrap(rows, f"performance_reviews 表 (模板: employee-kpi, {_now()})")


def get_projects_by_status(status: str) -> str:
    rows = _query(
        "SELECT p.project_id, p.name, e.name AS lead_name, p.start_date, p.end_date, p.budget "
        "FROM projects p "
        "LEFT JOIN employees e ON p.lead_id = e.employee_id "
        "WHERE p.status = ?",
        (status,),
    )
    _log.info("get_projects_by_status(%s) -> %d rows", status, len(rows))
    return _wrap(rows, f"projects 表 (模板: projects-by-status, {_now()})")


# ═══════════════════════════════════════════
# 安全 SQL 审核通道
# ═══════════════════════════════════════════

def safe_query(sql: str, params: list) -> str:
    t0 = time.time()
    try:
        cleaned = audit(sql, params)
    except Exception as e:
        _log.warning("safe_query AUDIT REJECTED: %s | sql=%s", e, sql[:100])
        return _wrap({"error": f"SQL 审核不通过: {e}"}, "审核拒绝")

    source_label = f"数据库查询 (SQL: {cleaned[:80]}..., {_now()})"
    try:
        rows = _query(cleaned, tuple(params))
        _log.info("safe_query OK -> %d rows (%.1fms)", len(rows), (time.time()-t0)*1000)
        return _wrap(rows, source_label)
    except Exception as e:
        _log.error("safe_query EXEC FAILED: %s", e)
        return _wrap({"error": f"查询执行失败: {e}"}, source_label)
