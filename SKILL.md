# enterprise-qa

企业智能问答助手 — 查询员工信息、项目记录、考勤数据、绩效考核，以及检索公司制度、技术规范、会议纪要等知识库文档。

## 触发词

`/enterprise-qa <问题>` 或 `/qa <问题>`

## 可用工具

所有命令从 skill 根目录执行：`cd .claude/skills/enterprise-qa`

### 数据库模板查询

| 命令 | 用途 |
|------|------|
| `python -m src.cli employee-info --name "<姓名>"` | 员工基本信息 |
| `python -m src.cli employee-projects --name "<姓名>"` | 员工参与的项目及角色 |
| `python -m src.cli department-count --dept "<部门>"` | 部门在职人数 |
| `python -m src.cli department-employees --dept "<部门>"` | 部门员工列表 |
| `python -m src.cli monthly-attendance --name "<姓名>" --month "YYYY-MM"` | 月度考勤统计 |
| `python -m src.cli employee-kpi --name "<姓名>" --year YYYY` | 年度 KPI 记录 |
| `python -m src.cli projects-by-status --status <状态>` | 按状态查项目 |

### 安全 SQL 通道

模板无法满足时使用。**必须参数化** — 条件值用 `?` 占位，实际值通过 `--params` 传入 JSON 数组：

```bash
python -m src.cli query --sql "SELECT <列> FROM <表> WHERE <条件> = ?" --params '["<值>"]'
```

限制：仅 SELECT、表名白名单 (employees/projects/project_members/attendance/performance_reviews)、禁止 `manager_id`。违规 SQL 会被审核层自动拒绝。

### 知识库检索

```bash
python -m src.cli search-kb --query "<查询词>"
python -m src.cli list-docs
```

### 工具

```bash
python -m src.cli get-schema   # 查看表结构，写 SQL 时参考
```

## 执行流程

1. **分类**：判断问题属于纯 DB / 纯 KB / 混合
   - DB 优先选模板命令，模板不覆盖时用安全 SQL 通道
   - KB 用 `search-kb`
   - 混合查询同时调用 DB + KB
2. **查询**：执行对应命令获取数据
3. **回答**：自然语言组织，引用返回结果的 `_source` 字段作为来源标注
   - 混合查询用表格对照「条件/要求/实际情况/结果」
   - 格式：`> 来源：<直接使用 _source 的值>`

## 返回格式说明

所有命令返回统一 JSON 格式：

```json
{"data": [...], "_source": "employees 表 (模板: employee-info, 2026-03-27 14:30:00)"}
```

- `data`：结果数组（可能为空）
- `_source`：数据来源标注，直接用于答案引用

## 边界规则

- **查无此人**：先按姓名查，无结果再按 `employee_id` 查，仍无则明确告知"未找到该员工"
- **查无此知识**：告知"知识库中未找到相关信息"，不编造
- **SQL 被拒**：审核层拒绝时返回 `{"data": {"error": "SQL 审核不通过: ..."}}`，告知用户查询被安全策略拦截
- **资料不足**：明确列出已验证和无法判断的条件，给出明确结论
- **模糊问题**：引导用户补充姓名、部门、时间等关键信息

## 当前环境

- 当前日期：2026 年 3 月 27 日
- 时区：Asia/Shanghai
- 数据库：enterprise.db (SQLite，5 张表)
- 知识库：knowledge/ (7 份文档)
- 考勤数据：仅 2026 年 2 月
- 绩效数据：仅 2025 年 (4 季度)
