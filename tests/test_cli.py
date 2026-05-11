"""CLI 集成测试 — T01-T12 + 来源标注验证"""
import json
import subprocess
import sys
import os
import pytest

from unittest import mock
from src.cli import main as cli_main


def _data(output: str):
    """解析 CLI 输出，返回 (data, source)"""
    parsed = json.loads(output)
    return parsed.get("data", parsed), parsed.get("_source", "")


def _run_cli(*args):
    env = os.environ.copy()
    env["ENTERPRISE_QA_DB_PATH"] = os.environ.get("ENTERPRISE_QA_DB_PATH", "./enterprise.db")
    env["ENTERPRISE_QA_KB_PATH"] = os.environ.get("ENTERPRISE_QA_KB_PATH", "./knowledge")

    result = subprocess.run(
        [sys.executable, "-m", "src.cli"] + list(args),
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    return result.stdout.strip()


class TestCLIMainDispatch:
    """直接调用 main() 覆盖 CLI dispatch"""

    def test_employee_info_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cli.py", "employee-info", "--name", "张三"])
        try: cli_main()
        except SystemExit: pass
        data, src = _data(capsys.readouterr().out)
        assert data[0]["department"] == "研发部"
        assert "employees" in src

    def test_department_count_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cli.py", "department-count", "--dept", "研发部"])
        try: cli_main()
        except SystemExit: pass
        data, src = _data(capsys.readouterr().out)
        assert data[0]["count"] == 4

    def test_search_kb_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cli.py", "search-kb", "--query", "年假"])
        try: cli_main()
        except SystemExit: pass
        data, src = _data(capsys.readouterr().out)
        assert len(data) > 0

    def test_get_schema_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cli.py", "get-schema"])
        try: cli_main()
        except SystemExit: pass
        assert "employees" in capsys.readouterr().out

    def test_list_docs_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cli.py", "list-docs"])
        try: cli_main()
        except SystemExit: pass
        out = capsys.readouterr().out
        data, src = _data(out)
        assert len(data) > 0
        assert "_source" in out

    def test_query_main(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "cli.py", "query",
            "--sql", "SELECT email FROM employees WHERE name = ?",
            "--params", '["张三"]',
        ])
        try: cli_main()
        except SystemExit: pass
        data, src = _data(capsys.readouterr().out)
        assert data[0]["email"] == "zhangsan@company.com"


class TestBasicDB:
    """T01, T02"""

    def test_t01_zhangsan_department(self):
        data, src = _data(_run_cli("employee-info", "--name", "张三"))
        assert data[0]["department"] == "研发部"

    def test_t02_lisi_exists(self):
        data, src = _data(_run_cli("employee-info", "--name", "李四"))
        assert data[0]["employee_id"] == "EMP-002"


class TestBasicKB:
    """T03, T04"""

    def test_t03_annual_leave(self):
        data, src = _data(_run_cli("search-kb", "--query", "年假怎么算"))
        assert len(data) > 0

    def test_t04_late_rule(self):
        data, src = _data(_run_cli("search-kb", "--query", "迟到几次扣钱"))
        assert len(data) > 0


class TestCrossTable:
    """T05, T06, T07, T08"""

    def test_t05_zhangsan_projects(self):
        data, src = _data(_run_cli("employee-projects", "--name", "张三"))
        assert len(data) == 4

    def test_t06_rd_count(self):
        data, src = _data(_run_cli("department-count", "--dept", "研发部"))
        assert data[0]["count"] == 4

    def test_t07_wangwu_kpi(self):
        outputs = _run_cli("employee-kpi", "--name", "王五", "--year", "2025")
        data, src = _data(outputs)
        avg = sum(r["kpi_score"] for r in data) / len(data)
        assert avg == 80.0

    def test_t08_zhangsan_late_feb(self):
        data, src = _data(_run_cli("monthly-attendance", "--name", "张三", "--month", "2026-02"))
        late_count = sum(r["count"] for r in data if r["status"] == "late")
        assert late_count == 2


class TestEdgeCases:
    """T09-T12"""

    def test_t09_employee_not_found(self):
        data, src = _data(_run_cli("employee-info", "--name", "EMP-999"))
        assert data == []

    def test_t11_sql_injection_rejected(self):
        out = _run_cli("query", "--sql", "DELETE FROM employees WHERE name = ?", "--params", '["张三"]')
        assert "error" in out

    def test_t11_sensitive_column_rejected(self):
        """敏感列 manager_id 被拦截"""
        out = _run_cli("query", "--sql", "SELECT manager_id FROM employees WHERE name = ?", "--params", '["张三"]')
        parsed = json.loads(out)
        assert "error" in str(parsed) or "审核" in str(parsed)

    def test_t12_kb_no_fabrication(self):
        data, src = _data(_run_cli("search-kb", "--query", "xyzabc123 不存在的东西"))
        assert isinstance(data, list)

    def test_source_in_all_responses(self):
        """所有查询都应包含 _source"""
        out = _run_cli("employee-info", "--name", "张三")
        assert "_source" in out


class TestQueryChannel:
    """安全 SQL 通道"""

    def test_query_budget(self):
        data, src = _data(_run_cli(
            "query", "--sql", "SELECT name, budget FROM projects WHERE project_id = ?",
            "--params", '["PRJ-003"]',
        ))
        assert data[0]["budget"] == 800000

    def test_query_normal_select(self):
        data, src = _data(_run_cli(
            "query", "--sql", "SELECT name FROM employees WHERE department = ? AND status = ?",
            "--params", '["研发部", "active"]',
        ))
        names = [r["name"] for r in data]
        assert "张三" in names
