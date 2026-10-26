# Felix Skills

面向 Java 与 MySQL 开发场景的 Agent Skills：把故障排查、代码审查与 SQL 分析经验整理成可复用流程。

| Skill | 入口 | 交付 |
| --- | --- | --- |
| incident-evidence-triage | [故障证据初查](skills/incident-evidence-triage/SKILL.md) | 跨系统时间线、证据链与最小验证步骤 |
| java-incident-triage | [故障初查](skills/java-incident-triage/SKILL.md) | 证据、原因判断与下一步检查 |
| java-change-review | [变更审查](skills/java-change-review/SKILL.md) | 有位置、触发条件和影响的缺陷报告 |
| mysql-query-review | [SQL 审查](skills/mysql-query-review/SKILL.md) | SQL 语法检查、查询优化、索引与执行计划分析 |

## 安装与使用

每个 `skills/<名称>/` 是独立技能包。把所选目录整体导入支持 Agent Skills 的客户端，不要只复制 SKILL.md，否则相对引用会缺失。具体安装入口以客户端说明为准；本仓库还未进行 WorkBuddy 等客户端的实际加载测试。

这些技能可基于本地材料工作，不要求常驻 Python 服务、API Key 或 MCP。incident-evidence-triage 还可利用已有且获授权的 MCP 连接进行只读取证；仓库不附带具体平台的 MCP server。Java/MySQL 分析技能仅分析用户材料时无需 Java 运行环境；读取仓库差异需要 Git，执行测试时才需要项目要求的 JDK 与构建工具。这里的分析输出不是运行过线上诊断的证明。

示例请求：

- “使用 java-incident-triage 分析这些日志和线程栈，区分已确认原因与缺失证据，只分析材料。”
- “使用 java-change-review 审查我指定的 base 到 HEAD 的 Java 变更，先给报告，不修改代码。”

这些技能默认不连接生产环境、不执行自动修复、不发送消息。可以在后续明确授权的任务中继续采集或修复；没有配置通知 MCP 也不影响使用。

## 验证与版本状态

首版已提供通用格式与可独立阅读的参考资料。合成验证案例见 [evaluations/cases.md](evaluations/cases.md)，答案与判定标准放在 [evaluations/rubric.md](evaluations/rubric.md)，执行记录见 [evaluations/validation.md](evaluations/validation.md)。格式通过不代表客户端行为已验证。

原创代码与说明采用 [MIT License](LICENSE)，业务边界与第三方资源说明见 [免责声明](DISCLAIMER.md)。第三方资源不因该许可证获得重新授权。目前尚未发布 SkillHub 或 GitHub Release。

## 编写约定

- 一个技能解决一类明确任务，name 与目录相同。
- 主文件写关键步骤，参考资料按症状或审查范围加载。
- 使用相对路径，不依赖作者的电脑目录、内部服务或私有笔记。
- 案例使用合成、脱敏材料，不提交日志原件、凭证或堆转储。
- 框架行为以目标版本为准；知识不能替代项目现场证据。

格式依据：[Agent Skills](https://agentskills.io/specification)。

## MySQL 查询审查

`mysql-query-review` 聚焦 SQL 语法检查、查询优化、索引设计与执行计划分析。提供 SQL 即可先做静态检查；补充版本、表结构、现有索引和计划后，可进一步核对字段、索引匹配与访问成本。

示例：“使用 mysql-query-review，检查下面 SQL 的语法、优化方向和索引；说明依据及验证步骤，只分析材料，不执行数据库操作。”

该技能不包含行业业务公式审计。静态检查不等于目标 MySQL 已验证通过，也不保证发现所有错误；没有实测不承诺提速比例。不需要数据库账号、MCP 或独立程序，不自动执行 SQL 或创建索引。

试用见[日期条件优化 Demo](skills/mysql-query-review/examples/optimization.md)。安装时复制整个 `skills/mysql-query-review/` 目录，保留 references、examples 和 LICENSE。

[评估输入](evaluations/mysql-cases.md)与[评判标准](evaluations/mysql-rubric.md)独立保存，执行范围见[验证记录](evaluations/validation.md)。当前未完成全量独立行为测试或真实数据库性能验证。
