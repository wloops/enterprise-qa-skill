# 企业智能问答助手

## 安装

```bash
# 1. 复制到目标项目的 .claude/skills/ 目录
cp -r enterprise-qa /path/to/project/.claude/skills/enterprise-qa

# 2. 安装 Python 依赖
cd .claude/skills/enterprise-qa
pip install -r requirements.txt

# 3. 初始化数据库（跨平台 Python 版）
python init_db.py

# 4. 配置数据源（二选一）
# 方式 A：环境变量
export ENTERPRISE_QA_DB_PATH="./enterprise.db"
export ENTERPRISE_QA_KB_PATH="./knowledge"
# 方式 B：编辑 config.yaml

# 5. 验证安装
python -m pytest tests/ -q
```

> **兼容性**：Python 3.10+，Mac / Linux / Windows 通用，纯 Python 无系统依赖。

## 触发词

`/enterprise-qa <问题>` 或 `/qa <问题>`

## 功能

回答公司内部的员工工作相关问题，自动查询数据库（员工/项目/考勤/绩效）和知识库（制度/规范/会议纪要），生成准确且有依据的回答。

## 工具命令

以下所有命令在 skills 目录下执行：
```bash
cd .claude/skills/enterprise-qa
```

### 数据库模板查询

| 命令 | 说明 |
|------|------|
| `python -m src.cli employee-info --name "<姓名>"` | 按姓名查询员工基本信息 |
| `python -m src.cli employee-projects --name "<姓名>"` | 查询员工参与的所有项目及角色 |
| `python -m src.cli department-count --dept "<部门>"` | 查询部门在职人数 |
| `python -m src.cli department-employees --dept "<部门>"` | 查询部门员工列表 |
| `python -m src.cli monthly-attendance --name "<姓名>" --month "YYYY-MM"` | 查询某月员工考勤统计 |
| `python -m src.cli employee-kpi --name "<姓名>" --year YYYY` | 查询员工某年 KPI 记录 |
| `python -m src.cli projects-by-status --status <状态>` | 按状态查项目列表 |

### 安全 SQL 通道（灵活查询）

当模板无法满足需求时，使用此通道。**必须使用参数化查询**：
```bash
python -m src.cli query --sql "SELECT <列> FROM <表> WHERE <条件> = ?" --params '["<值>"]'
```

**重要安全规则**：
- SQL 中的值必须用 `?` 占位，实际值通过 `--params` 传入
- 只允许 SELECT，表名仅限于：employees, projects, project_members, attendance, performance_reviews
- **禁止直接查询 `manager_id`**，需要上级姓名时应通过 JOIN employees 获取
- 审核层会自动拒绝不合规的 SQL

### 知识库检索

```bash
python -m src.cli search-kb --query "<查询词>"
python -m src.cli list-docs
```

### 工具命令

```bash
python -m src.cli get-schema    # 查看数据库表结构
```

## 工作流程

1. **分析问题**：判断属于以下哪类
   - 纯 DB 查询：优先使用模板命令
   - 纯 KB 查询：使用 search-kb
   - 混合查询：同时调用 DB 和 KB 命令
   - 需要灵活 SQL：使用 query 命令（遵守安全规则）

2. **执行查询**：调用对应的 CLI 命令获取数据。
   所有命令返回格式为 `{"data": [...], "_source": "..."}`。
   `data` 为查询结果数组，`_source` 为自动生成的来源标注。

3. **生成回答**：
   - 用自然语言组织答案
   - 混合查询时，将 DB 数据与 KB 规则对照分析
   - 以表格形式呈现对比分析（参照笔试要求格式）
   - **直接引用** `_source` 字段的值作为来源标注：
     ```
     > 来源：<直接使用返回的 _source 值>
     ```

## 边界处理

- **无匹配员工**：先按姓名查，无结果再按 employee_id 查。仍无结果则明确告知
- **无匹配知识**：告知"知识库中未找到相关信息"
- **SQL 注入企图**：审核层自动拦截并返回错误
- **模糊问题**：引导用户提供更多信息（姓名、部门、时间等）
- **信息不足**：如实说明哪些条件无法判断，不编造答案

## 当前环境

- 当前日期：2026 年 3 月 27 日
- 时区：Asia/Shanghai
- 数据库：SQLite (enterprise.db)
- 知识库：knowledge/ 目录
- 考勤数据仅有 2026 年 2 月
- 绩效数据仅有 2025 年（4 个季度）

## 输出格式示例

### 纯 DB 查询
```
张三的邮箱是 zhangsan@company.com。

> 来源：employees 表 (employee_id: EMP-001)
```

### 纯 KB 查询
```
根据《人事制度》，年假计算规则为：
- 入职满 1 年享 5 天
- 每增 1 年 +1 天
- 上限 15 天

> 来源：hr_policies.md §请假类型
```

### 混合查询
使用表格对比条件与实际情况，明确标注各条件满足与否，最终给出结论和建议。
