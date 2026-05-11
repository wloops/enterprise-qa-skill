"""
CLI 入口 — 为 Claude 提供可调用的数据查询工具
"""
import argparse
import json
import sys

from .db import (
    get_employee,
    get_employee_projects,
    get_department_count,
    get_department_employees,
    get_monthly_attendance,
    get_employee_kpi,
    get_projects_by_status,
    safe_query,
)
from .kb import search_kb, list_docs

SCHEMA_HELP = """
表结构:
  employees      — employee_id, name, department, level, hire_date, manager_id, email, status
  projects       — project_id, name, lead_id, status, start_date, end_date, budget
  project_members— project_id, employee_id, role, join_date
  attendance     — id, employee_id, date, status
  performance_reviews — id, employee_id, year, quarter, kpi_score, grade

查询模板: employee-info | employee-projects | department-count | department-employees
           monthly-attendance | employee-kpi | projects-by-status
灵活查询: query --sql "SELECT ... WHERE ... = ?" --params '["val"]'
知识库:   search-kb --query "问题"
""".strip()


def main():
    parser = argparse.ArgumentParser(description="企业智能问答助手 - 数据查询工具")
    sub = parser.add_subparsers(dest="command")

    # 模板查询
    sub.add_parser("employee-info").add_argument("--name", required=True)
    sub.add_parser("employee-projects").add_argument("--name", required=True)
    sp = sub.add_parser("department-count")
    sp.add_argument("--dept", required=True)
    sp = sub.add_parser("department-employees")
    sp.add_argument("--dept", required=True)
    sp = sub.add_parser("monthly-attendance")
    sp.add_argument("--name", required=True)
    sp.add_argument("--month", required=True)
    sp = sub.add_parser("employee-kpi")
    sp.add_argument("--name", required=True)
    sp.add_argument("--year", type=int, default=2025)
    sp = sub.add_parser("projects-by-status")
    sp.add_argument("--status", required=True)

    # 安全 SQL 通道
    sp = sub.add_parser("query")
    sp.add_argument("--sql", required=True)
    sp.add_argument("--params", type=json.loads, default=[])

    # 知识库
    sp = sub.add_parser("search-kb")
    sp.add_argument("--query", required=True)
    sp.add_argument("--top-k", type=int, default=5)

    # 工具
    sub.add_parser("list-docs")
    sub.add_parser("get-schema")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 路由
    dispatch = {
        "employee-info": lambda: get_employee(args.name),
        "employee-projects": lambda: get_employee_projects(args.name),
        "department-count": lambda: get_department_count(args.dept),
        "department-employees": lambda: get_department_employees(args.dept),
        "monthly-attendance": lambda: get_monthly_attendance(args.name, args.month),
        "employee-kpi": lambda: get_employee_kpi(args.name, args.year),
        "projects-by-status": lambda: get_projects_by_status(args.status),
        "query": lambda: safe_query(args.sql, args.params),
        "search-kb": lambda: search_kb(args.query, args.top_k),
        "list-docs": lambda: list_docs(),
        "get-schema": lambda: SCHEMA_HELP,
    }

    result = dispatch[args.command]()
    print(result)


if __name__ == "__main__":
    main()
