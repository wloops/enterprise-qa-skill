"""模板查询函数测试"""
import json
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def setup_db(test_db, monkeypatch):
    from src import config
    monkeypatch.setattr(config.config, "db_path", test_db)


from src.db import (
    get_employee,
    get_employee_projects,
    get_department_count,
    get_department_employees,
    get_monthly_attendance,
    get_employee_kpi,
    get_projects_by_status,
    safe_query,
)


def _data(fn, *args):
    """调用查询函数，返回 data 数组"""
    result = json.loads(fn(*args))
    return result["data"], result["_source"]


def _data0(fn, *args):
    return _data(fn, *args)[0]


class TestEmployeeInfo:
    """T01, T02, T09"""

    def test_get_by_name(self):
        rows, src = _data(get_employee, "张三")
        assert len(rows) == 1
        assert rows[0]["department"] == "研发部"
        assert rows[0]["email"] == "zhangsan@company.com"
        assert "manager_id" not in rows[0]  # 敏感字段不出现在结果中
        assert "employees" in src

    def test_get_by_id(self):
        rows, src = _data(get_employee, "EMP-002")
        assert rows[0]["name"] == "李四"

    def test_not_found(self):
        rows, src = _data(get_employee, "EMP-999")
        assert rows == []

    def test_resigned_excluded(self):
        rows, _ = _data(get_employee, "离职员工")
        assert rows == []

    def test_source_annotation(self):
        _, src = _data(get_employee, "张三")
        assert "_source" in json.dumps({"_source": src})


class TestEmployeeProjects:
    """T05"""

    def test_zhangsan_projects(self):
        rows, src = _data(get_employee_projects, "张三")
        assert len(rows) == 4
        roles = {r["name"]: r["role"] for r in rows}
        assert roles["ReMe 记忆框架"] == "lead"
        assert roles["智能问答系统"] == "core"
        assert "project_members" in src

    def test_wangwu_projects(self):
        rows, _ = _data(get_employee_projects, "王五")
        assert len(rows) == 1
        assert rows[0]["name"] == "官网改版"


class TestDepartment:
    """T06"""

    def test_rd_count(self):
        rows, src = _data(get_department_count, "研发部")
        assert rows[0]["count"] == 4

    def test_rd_employees(self):
        rows, _ = _data(get_department_employees, "研发部")
        names = {r["name"] for r in rows}
        assert names == {"张三", "李四", "钱七", "周九"}

    def test_product_count(self):
        rows, _ = _data(get_department_count, "产品部")
        assert rows[0]["count"] == 3


class TestAttendance:
    """T08"""

    def test_zhangsan_feb(self):
        rows, src = _data(get_monthly_attendance, "张三", "2026-02")
        stats = {r["status"]: r["count"] for r in rows}
        assert stats.get("late", 0) == 2

    def test_wangwu_feb(self):
        rows, _ = _data(get_monthly_attendance, "王五", "2026-02")
        stats = {r["status"]: r["count"] for r in rows}
        assert stats.get("late", 0) == 5


class TestKPI:
    """T07"""

    def test_wangwu_kpi(self):
        rows, _ = _data(get_employee_kpi, "王五", 2025)
        scores = [r["kpi_score"] for r in rows]
        assert sum(scores) / len(scores) == 80.0

    def test_zhangsan_kpi(self):
        rows, _ = _data(get_employee_kpi, "张三", 2025)
        avg = sum(r["kpi_score"] for r in rows) / 4
        assert avg == 89.25

    def test_lisi_kpi(self):
        rows, _ = _data(get_employee_kpi, "李四", 2025)
        grades = [r["grade"] for r in rows]
        assert grades.count("S") == 3


class TestProjectsByStatus:
    """追加题"""

    def test_active(self):
        rows, _ = _data(get_projects_by_status, "active")
        names = {r["name"] for r in rows}
        assert "ReMe 记忆框架" in names
        assert len(names) == 2


class TestSafeQueryChannel:
    """安全 SQL 审核通道"""

    def test_simple_select(self):
        rows, src = _data(safe_query,
            "SELECT email FROM employees WHERE name = ?", ["张三"])
        assert rows[0]["email"] == "zhangsan@company.com"
        assert "employees" in src

    def test_injection_rejected(self):
        result = json.loads(
            safe_query("DELETE FROM employees WHERE name = ?", ["张三"])
        )
        assert "error" in str(result)

    def test_empty_result(self):
        rows, _ = _data(safe_query,
            "SELECT * FROM employees WHERE name = ?", ["不存在"])
        assert rows == []

    def test_sensitive_column_rejected(self):
        """敏感列 manager_id 被拦截"""
        result = json.loads(
            safe_query("SELECT manager_id FROM employees WHERE name = ?", ["张三"])
        )
        assert "error" in str(result) or "审核" in str(result)
