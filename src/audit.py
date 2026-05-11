"""
SQL 审核层 — 4 道安全检查
"""
import re

# 允许的表名白名单
ALLOWED_TABLES = {
    "employees",
    "projects",
    "project_members",
    "attendance",
    "performance_reviews",
}

# 禁止的 SQL 关键词（非 SELECT 操作）
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "ATTACH", "DETACH", "PRAGMA", "REPLACE", "TRUNCATE", "GRANT",
    "REVOKE", "VACUUM", "REINDEX",
]

# 敏感列黑名单 — SELECT 中禁止直接查询
SENSITIVE_COLUMNS = {"manager_id"}

# 禁止的多语句分隔符
MULTI_STATEMENT_RE = re.compile(r";\s*(?=\w|\")", re.IGNORECASE)

# 提取 FROM / JOIN 表名的正则
TABLE_NAME_RE = re.compile(
    r'\b(?:FROM|JOIN)\s+["`]?(\w+)["`]?',
    re.IGNORECASE,
)

# 提取 SELECT 列名的正则
COLUMN_NAME_RE = re.compile(
    r'SELECT\s+(.+?)\s+FROM',
    re.IGNORECASE | re.DOTALL,
)


class AuditError(Exception):
    """审核拒绝异常"""
    pass


def audit(sql: str, params: list) -> str:
    """对 SQL 执行 4 道安全检查，通过则返回清洗后的 SQL，否则抛 AuditError。

    Args:
        sql: Claude 生成的 SQL 语句
        params: 参数列表

    Returns:
        清洗后的 SQL 语句

    Raises:
        AuditError: 审核不通过
    """
    sql_stripped = sql.strip()

    # ---- 第 1 道：仅允许 SELECT ----
    sql_upper = sql_stripped.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # 用词边界匹配，避免误杀 SELECT 本身
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            raise AuditError(f"禁止的 SQL 操作: {keyword}")

    if not re.match(r'^\s*SELECT\b', sql_upper):
        raise AuditError("仅允许 SELECT 查询")

    # ---- 第 2 道：表名白名单 ----
    table_refs = TABLE_NAME_RE.findall(sql_stripped)
    for tbl in table_refs:
        if tbl.lower() not in ALLOWED_TABLES:
            raise AuditError(f"表不在白名单中: {tbl}")

    # ---- 第 3 道：禁止多语句 ----
    # 检查是否有分号（排除字符串内的分号）
    if ";" in sql_stripped.rstrip(";"):
        raise AuditError("禁止多语句查询")

    # ---- 第 4 道：参数化强制 ----
    placeholder_count = sql_stripped.count("?")
    if placeholder_count != len(params):
        raise AuditError(
            f"参数数量不匹配: SQL 中有 {placeholder_count} 个占位符, 传入了 {len(params)} 个参数"
        )

    # ---- 第 5 道：敏感列过滤 ----
    col_match = COLUMN_NAME_RE.search(sql_stripped)
    if col_match:
        cols = col_match.group(1)
        for col in cols.split(","):
            col_name = col.strip().split()[-1].strip("`\"'")  # 处理 "e.manager_id" 等形式
            if "." in col_name:
                col_name = col_name.split(".")[-1]
            if col_name.lower() in SENSITIVE_COLUMNS:
                raise AuditError(f"禁止查询敏感列: {col_name}（请通过 JOIN employees 获取上级姓名替代）")

    return sql_stripped
