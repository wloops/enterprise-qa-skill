# 企业智能问答助手 Skill

基于 Claude Code Skill 的企业内部智能问答系统，支持自然语言查询员工信息、项目记录、考勤数据、绩效数据，以及检索公司制度、技术规范、会议纪要等知识库文档。

## 架构

```
用户问题 → Claude (意图识别) → Python CLI 工具 → SQLite / 知识库 → 综合答案
                                    ├── 模板查询 (7 个高频接口)
                                    ├── 安全 SQL 通道 (5 道审核)
                                    └── BM25 知识库检索
```

每个查询结果自动附带 `_source` 来源标注。

## 安装

```bash
# 1. 复制到目标项目
cp -r enterprise-qa /path/to/project/.claude/skills/enterprise-qa

# 2. 安装依赖 (Python 3.10+)
cd .claude/skills/enterprise-qa
pip install -r requirements.txt

# 3. 初始化数据库
python init_db.py

# 4. 配置数据源 (二选一)
# 方式 A — 环境变量:
export ENTERPRISE_QA_DB_PATH="./enterprise.db"
export ENTERPRISE_QA_KB_PATH="./knowledge"
# 方式 B — 编辑 config.yaml
```

> 跨平台：Mac / Linux / Windows 通用，纯 Python 实现，无系统依赖。

## 使用

在 Claude Code 中通过触发词调用：

```bash
/enterprise-qa "张三的部门是什么？"
/enterprise-qa "年假怎么计算？"
/qa "王五符合 P5 晋升 P6 条件吗？"
```

也可以直接调用 CLI：

```bash
python -m src.cli employee-info --name "张三"
python -m src.cli search-kb --query "年假怎么算"
python -m src.cli employee-kpi --name "王五" --year 2025
python -m src.cli query --sql "SELECT email FROM employees WHERE name = ?" --params '["张三"]'
```

## 支持的查询类型

| 类型 | 示例 | 实现 |
|------|------|------|
| 纯数据库查询 | "张三的邮箱是多少？" | 模板 / 安全 SQL 通道 |
| 纯知识库查询 | "年假怎么算？" | BM25 检索 |
| 混合查询 | "王五符合晋升条件吗？" | DB + KB 融合 |
| 跨表关联 | "研发部有哪些在研项目？" | JOIN 查询 |
| 时间范围 | "张三上个月迟到几次？" | 月度考勤统计 |

## 安全设计

- **5 道 SQL 审核**：仅允许 SELECT、表名白名单、禁止多语句、参数化强制、敏感列过滤
- **全参数化查询**：杜绝 SQL 注入
- **敏感字段保护**：`manager_id` 等字段禁止直接查询
- **路径可配置**：数据库/知识库路径通过环境变量或配置文件管理

## 测试

```bash
python -m pytest tests/ -v --cov=src --cov-report=term
```

覆盖率 94%，71 个测试用例，覆盖全部 12 个官方测试用例 (T01-T12)。

## 技术栈

- Python 3.10+
- SQLite (标准库)
- BM25 检索 (rank-bm25)
- pytest (测试框架)

## 目录结构

```
enterprise-qa/
├── README.md
├── SKILL.md               # Claude 执行指令
├── requirements.txt
├── config.yaml
├── init_db.py             # 数据库初始化
├── enterprise.db          # SQLite 数据库
├── knowledge/             # 知识库文档 (7 份)
├── src/
│   ├── cli.py             # CLI 入口
│   ├── db.py              # 数据库查询 + 安全审核通道
│   ├── audit.py           # SQL 审核层 (5 道检查)
│   ├── kb.py              # 知识库检索
│   ├── config.py          # 配置加载
│   └── logger.py          # 日志系统
└── tests/
    ├── conftest.py
    ├── test_db.py
    ├── test_audit.py
    ├── test_kb.py
    └── test_cli.py
```
