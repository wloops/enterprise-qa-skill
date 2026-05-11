"""pytest fixtures — 临时数据库 + 知识库"""
import json
import os
import pytest
import sqlite3
import tempfile
from pathlib import Path


SEED_SQL = """
INSERT INTO employees VALUES
('EMP-000', 'CEO', '管理层', 'P10', '2020-01-01', NULL, 'ceo@company.com', 'active'),
('EMP-001', '张三', '研发部', 'P6', '2023-06-15', 'EMP-000', 'zhangsan@company.com', 'active'),
('EMP-002', '李四', '研发部', 'P7', '2022-03-01', 'EMP-000', 'lisi@company.com', 'active'),
('EMP-003', '王五', '产品部', 'P5', '2024-01-10', 'EMP-004', 'wangwu@company.com', 'active'),
('EMP-004', '赵六', '产品部', 'P6', '2021-09-20', 'EMP-000', 'zhaoliu@company.com', 'active'),
('EMP-005', '钱七', '研发部', 'P5', '2025-02-01', 'EMP-002', 'qianqi@company.com', 'active'),
('EMP-006', '孙八', '市场部', 'P6', '2023-03-15', 'EMP-000', 'sunba@company.com', 'active'),
('EMP-007', '周九', '研发部', 'P7', '2021-06-01', 'EMP-000', 'zhoujiu@company.com', 'active'),
('EMP-008', '吴十', '产品部', 'P4', '2025-07-01', 'EMP-004', 'wushi@company.com', 'active'),
('EMP-009', '离职员工', '研发部', 'P5', '2022-01-01', 'EMP-002', 'left@company.com', 'resigned');

INSERT INTO projects VALUES
('PRJ-001', 'ReMe 记忆框架', 'EMP-001', 'active', '2026-01-01', NULL, 500000),
('PRJ-002', '智能问答系统', 'EMP-002', 'planning', '2026-03-01', NULL, 300000),
('PRJ-003', '移动端 App', 'EMP-007', 'active', '2025-06-01', '2026-06-01', 800000),
('PRJ-004', '数据分析平台', 'EMP-001', 'completed', '2025-01-01', '2025-12-31', 400000),
('PRJ-005', '官网改版', 'EMP-006', 'on_hold', '2026-02-01', NULL, 150000);

INSERT INTO project_members VALUES
('PRJ-001', 'EMP-001', 'lead', '2026-01-01'),
('PRJ-001', 'EMP-002', 'core', '2026-01-15'),
('PRJ-001', 'EMP-005', 'contributor', '2026-02-01'),
('PRJ-002', 'EMP-002', 'lead', '2026-03-01'),
('PRJ-002', 'EMP-001', 'core', '2026-03-01'),
('PRJ-003', 'EMP-007', 'lead', '2025-06-01'),
('PRJ-003', 'EMP-001', 'contributor', '2025-08-01'),
('PRJ-004', 'EMP-001', 'lead', '2025-01-01'),
('PRJ-004', 'EMP-002', 'core', '2025-01-01'),
('PRJ-004', 'EMP-005', 'contributor', '2025-03-01'),
('PRJ-005', 'EMP-006', 'lead', '2026-02-01'),
('PRJ-005', 'EMP-003', 'core', '2026-02-15');

INSERT INTO attendance (employee_id, date, status) VALUES
('EMP-001', '2026-02-02', 'on_time'),
('EMP-001', '2026-02-04', 'late'),
('EMP-001', '2026-02-09', 'late'),
('EMP-003', '2026-02-02', 'late'),
('EMP-003', '2026-02-03', 'late'),
('EMP-003', '2026-02-05', 'late'),
('EMP-003', '2026-02-09', 'late'),
('EMP-003', '2026-02-12', 'late');

INSERT INTO performance_reviews (employee_id, year, quarter, kpi_score, grade) VALUES
('EMP-001', 2025, 1, 88, 'A'),
('EMP-001', 2025, 2, 92, 'A'),
('EMP-001', 2025, 3, 87, 'A'),
('EMP-001', 2025, 4, 90, 'A'),
('EMP-002', 2025, 1, 95, 'S'),
('EMP-002', 2025, 2, 93, 'S'),
('EMP-002', 2025, 3, 91, 'A'),
('EMP-002', 2025, 4, 94, 'S'),
('EMP-003', 2025, 3, 78, 'B'),
('EMP-003', 2025, 4, 82, 'B'),
('EMP-005', 2025, 2, 85, 'A'),
('EMP-005', 2025, 3, 83, 'B'),
('EMP-005', 2025, 4, 86, 'A');
"""

SCHEMA_SQL = """
CREATE TABLE employees (
    employee_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    department VARCHAR(50),
    level VARCHAR(20),
    hire_date DATE,
    manager_id VARCHAR(20),
    email VARCHAR(100),
    status VARCHAR(20)
);
CREATE TABLE projects (
    project_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    lead_id VARCHAR(20),
    status VARCHAR(20),
    start_date DATE,
    end_date DATE,
    budget DECIMAL(10,2)
);
CREATE TABLE project_members (
    project_id VARCHAR(20),
    employee_id VARCHAR(20),
    role VARCHAR(50),
    join_date DATE,
    PRIMARY KEY (project_id, employee_id)
);
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id VARCHAR(20),
    date DATE,
    status VARCHAR(10)
);
CREATE TABLE performance_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id VARCHAR(20),
    year INTEGER,
    quarter INTEGER,
    kpi_score DECIMAL(5,2),
    grade VARCHAR(2)
);
"""


@pytest.fixture
def test_db():
    """创建临时 SQLite 数据库，注入种子数据"""
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    conn.commit()
    conn.close()
    yield path
    os.close(fd)


@pytest.fixture
def test_kb_dir():
    """创建临时知识库目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "hr_policies.md").write_text(
            "# 人事制度\n\n## 考勤制度\n\n### 迟到规则\n"
            "月累计迟到 3 次以内不扣款，4-6 次每次扣款 50 元，7 次以上视为旷工 1 天。\n\n"
            "### 请假类型\n"
            "年假：入职满 1 年享 5 天，每增 1 年 +1 天，上限 15 天。\n"
            "病假：全薪 3 天/年需医院证明。\n",
            encoding="utf-8"
        )
        (root / "promotion_rules.md").write_text(
            "# 晋升评定标准\n\n## 晋升条件\n\n### P5 → P6\n"
            "入职满 1 年，连续 2 季度 KPI≥85，主导或核心参与项目≥3 个，无重大事故。\n\n"
            "### P6 → P7\n"
            "P6 满 2 年，连续 4 季度 KPI≥90，主导项目≥2 个，有技术突破或专利/论文。\n",
            encoding="utf-8"
        )
        yield str(root)
