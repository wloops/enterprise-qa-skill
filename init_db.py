#!/usr/bin/env python3
"""数据库初始化脚本（跨平台 Python 版，替代 init_db.sh）"""
import sqlite3
import sys
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / ".." / ".." / ".." / "enterprise-qa-data" / "schema.sql"
SEED = HERE / ".." / ".." / ".." / "enterprise-qa-data" / "seed_data.sql"
DB = HERE / "enterprise.db"


def main():
    # 查找 SQL 文件位置
    if SCHEMA.exists():
        schema_path, seed_path = SCHEMA, SEED
    else:
        # 如果数据文件已复制到 skill 目录下
        schema_path = HERE / "schema.sql"
        seed_path = HERE / "seed_data.sql"
        if not schema_path.exists():
            print("错误：未找到 schema.sql，请将 schema.sql 和 seed_data.sql 放在当前目录")
            sys.exit(1)

    print("=" * 50)
    print("  企业智能问答助手 - 数据库初始化")
    print("=" * 50)

    if DB.exists():
        DB.unlink()
        print("✓ 清理旧数据库...")

    conn = sqlite3.connect(str(DB))
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    print("✓ 创建表结构...")
    conn.executescript(seed_path.read_text(encoding="utf-8"))
    print("✓ 导入种子数据...")
    conn.commit()

    # 验证
    print()
    print("=" * 50)
    print("  数据验证")
    print("=" * 50)
    verifications = [
        ("员工数", "SELECT COUNT(*) FROM employees"),
        ("项目数", "SELECT COUNT(*) FROM projects"),
        ("项目成员数", "SELECT COUNT(*) FROM project_members"),
        ("考勤记录", "SELECT COUNT(*) FROM attendance"),
        ("绩效记录", "SELECT COUNT(*) FROM performance_reviews"),
    ]
    for label, sql in verifications:
        count = conn.execute(sql).fetchone()[0]
        print(f"  {label}：{count}")

    print()
    print("=" * 50)
    print("  快速测试")
    print("=" * 50)
    quick_tests = [
        ("张三的部门", "SELECT department FROM employees WHERE employee_id='EMP-001'"),
        ("研发部人数", "SELECT COUNT(*) FROM employees WHERE department='研发部' AND status='active'"),
        ("张三 2 月迟到", "SELECT COUNT(*) FROM attendance WHERE employee_id='EMP-001' AND status='late' AND date LIKE '2026-02-%'"),
    ]
    for label, sql in quick_tests:
        result = conn.execute(sql).fetchone()[0]
        print(f"  {label}：{result}")

    conn.close()
    print()
    print(f"✓ 数据库初始化完成：{DB}")
    print("=" * 50)


if __name__ == "__main__":
    main()
