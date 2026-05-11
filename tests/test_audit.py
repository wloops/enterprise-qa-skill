"""SQL 审核层测试"""
import pytest
from src.audit import audit, AuditError, ALLOWED_TABLES, SENSITIVE_COLUMNS


class TestAuditPass:
    """审核通过用例"""

    def test_simple_select(self):
        sql = audit("SELECT name FROM employees WHERE employee_id = ?", ["EMP-001"])
        assert "SELECT" in sql

    def test_select_with_join(self):
        sql = audit(
            "SELECT e.name, p.name FROM employees e "
            "JOIN project_members pm ON e.employee_id = pm.employee_id "
            "JOIN projects p ON pm.project_id = p.project_id "
            "WHERE e.name = ?",
            ["张三"],
        )
        assert "JOIN" in sql

    def test_select_count(self):
        sql = audit(
            "SELECT COUNT(*) FROM employees WHERE department = ? AND status = ?",
            ["研发部", "active"],
        )
        assert "COUNT" in sql

    def test_select_with_like(self):
        sql = audit(
            "SELECT * FROM attendance WHERE employee_id = ? AND date LIKE ?",
            ["EMP-001", "2026-02-%"],
        )
        assert "LIKE" in sql

    def test_all_allowed_tables(self):
        for table in ALLOWED_TABLES:
            sql = audit(f"SELECT * FROM {table} WHERE 1 = ?", [1])
            assert table.lower() in sql.lower()


class TestAuditReject:
    """审核拒绝用例"""

    def test_reject_insert(self):
        with pytest.raises(AuditError, match="INSERT"):
            audit("INSERT INTO employees VALUES ('X')", [])

    def test_reject_update(self):
        with pytest.raises(AuditError, match="UPDATE"):
            audit("UPDATE employees SET name = ?", ["hacker"])

    def test_reject_delete(self):
        with pytest.raises(AuditError, match="DELETE"):
            audit("DELETE FROM employees WHERE name = ?", ["张三"])

    def test_reject_drop(self):
        with pytest.raises(AuditError, match="DROP"):
            audit("DROP TABLE employees", [])

    def test_reject_alter(self):
        with pytest.raises(AuditError, match="ALTER"):
            audit("ALTER TABLE employees ADD COLUMN salary", [])

    def test_reject_create(self):
        with pytest.raises(AuditError, match="CREATE"):
            audit("CREATE TABLE hackers (id INT)", [])

    def test_reject_pragma(self):
        with pytest.raises(AuditError, match="PRAGMA"):
            audit("PRAGMA table_info(employees)", [])

    def test_reject_unknown_table(self):
        with pytest.raises(AuditError, match="白名单"):
            audit("SELECT * FROM users WHERE id = ?", [1])

    def test_reject_multiple_statements(self):
        with pytest.raises(AuditError):
            audit(
                "SELECT * FROM employees; SELECT * FROM employees",
                [],
            )

    def test_reject_param_count_mismatch(self):
        with pytest.raises(AuditError, match="参数数量不匹配"):
            audit("SELECT * FROM employees WHERE name = ? AND dept = ?", ["张三"])

    def test_reject_non_select_statement(self):
        with pytest.raises(AuditError, match="仅允许 SELECT"):
            audit("EXPLAIN SELECT * FROM employees", [])

    def test_reject_sensitive_column_manager_id(self):
        """5.3 敏感列过滤：禁止直接查询 manager_id"""
        with pytest.raises(AuditError, match="敏感列"):
            audit("SELECT manager_id FROM employees WHERE name = ?", ["张三"])

    def test_reject_sensitive_column_with_alias(self):
        """敏感列带表别名也应被拦截"""
        with pytest.raises(AuditError, match="敏感列"):
            audit("SELECT e.manager_id FROM employees e WHERE e.name = ?", ["张三"])


class TestSQLInjection:
    """SQL 注入攻击样本"""

    def test_injection_or_1_equals_1(self):
        sql = audit(
            "SELECT * FROM employees WHERE name = ? OR 1 = ?", ["张三", "1"]
        )
        assert "?" in sql

    def test_injection_union_select(self):
        with pytest.raises(AuditError, match="白名单"):
            audit(
                "SELECT name FROM employees WHERE name = ? UNION SELECT password FROM users WHERE ?",
                ["张三", "1"],
            )

    def test_injection_comment(self):
        try:
            sql = audit(
                "SELECT * FROM employees WHERE name = ? -- AND password = ?",
                ["张三"],
            )
        except AuditError as e:
            assert "参数" in str(e)
