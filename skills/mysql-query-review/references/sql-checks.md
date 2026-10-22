# SQL 语法、兼容性与改写检查

## 语法与名称解析

先检查完整语句及目标版本：括号/引号闭合、SELECT 列表与尾逗号、JOIN/ON、WHERE/GROUP BY/HAVING/ORDER BY/LIMIT 的结构、别名作用域、CTE 依赖和参数占位符。

不要机械把缺少逗号都认定为语法错：`SELECT id name FROM users` 可以把 name 解释为 id 的别名。先区分语法是否允许与是否符合用户意图。

表/列不存在属于名称解析问题。只有相应 DDL、视图定义或实际错误输出才可确认；没有元数据时只能说明待核对。没有真实 parser/server 结果，不写“语法验证通过”。

双引号的解释受 ANSI_QUOTES 影响，反斜杠转义受 NO_BACKSLASH_ESCAPES 影响；模式未知时不要断言同一引号写法在所有配置下都有效。

聚合合法性受 sql_mode 和函数依赖影响。ONLY_FULL_GROUP_BY 下，不能仅凭非聚合列未写进 GROUP BY 就断言报错；需检查主键/唯一非空约束形成的依赖及被 WHERE 限定为单值等情况。

WITH、窗口函数、JSON_TABLE 等按版本核对。MySQL 5.7、8.0 与 MariaDB 不能直接互用结论；“MySQL 8.0”有时还需小版本。语法修复并不证明查询结果或访问效率正确。

## 优化时必须保留的语义

- 一对多 JOIN 会影响行数；EXISTS 只判断存在，不能直接替换需要明细重复行的查询。
- LEFT JOIN 的右表条件移入/移出 WHERE 会改变 NULL 扩展行；不能只为优化而机械移动。
- NOT IN 的集合可能含 NULL 时，检查三值逻辑；COUNT(*)、COUNT(列)、COUNT(DISTINCT 列) 不可混用。
- UNION/UNION ALL、DISTINCT、聚合前后 LIMIT 均可能改变结果。避免以去重掩盖连接错误。
- 日期函数改为半开区间前，确认字段类型、参数、时区和边界。DATETIME、TIMESTAMP、字符串日期不能不加前提地互换。
- 深 OFFSET 的游标替代需要稳定排序和交互变化；任意跳页与游标翻页不等价。
- `ORDER BY sort` 默认升序，补充稳定键时可考虑 `ORDER BY sort ASC, id ASC`，不能直接改成 `sort DESC, id DESC`。实际决胜键应在结果集中唯一，不盲认JOIN后的id足够唯一。已有混合排序方向也需保留。
- 同值排序存在不确定性，不等于每次都会重复或漏行；需要分页方式、快照及并发条件才能判断跨页行为。即使顺序唯一，OFFSET分页在两次查询间插入或删除记录仍可能偏移。

这些检查用于保证优化不改坏查询语义，不扩展到行业金额、税率或结算政策判断。

## 动态 SQL 与 JSON

有最终生成 SQL 时优先检查最终语句；否则只分析已知构造过程和分支。MyBatis 的 `#{...}`、`${...}` 和 XML 标签属于模板语法，不直接当作最终 MySQL 语法错误；需要区分绑定占位与文本替换。`?` 参数标记也要放在预处理或驱动绑定上下文判断，不能假设复制到普通 SQL 控制台即可执行。PREPARE 并不天然表示注入，需具体核对值绑定、标识符白名单和转义。

GROUP_CONCAT 构造语句可能被长度上限截断，PREPARE 成功也不证明所有列都存在；核对实际生成内容、警告和预期长度，不只建议调大上限。

区分 SQL NULL、JSON null、空数组、缺失路径、数字/字符串 ID。JSON_TABLE 在 8.0.21 前后处理 JSON null 有差异；只有受目标数据和版本影响时再展开，不把所有 JSON 查询都判为错误或全扫描。

## 官方参考

- [MySQL 8.0 SQL 模式](https://dev.mysql.com/doc/refman/8.0/en/sql-mode.html)
- [MySQL 8.0 GROUP BY 处理](https://dev.mysql.com/doc/refman/8.0/en/group-by-handling.html)
- [MySQL 8.0 CTE](https://dev.mysql.com/doc/refman/8.0/en/with.html)
- [MySQL 8.0 JSON_TABLE](https://dev.mysql.com/doc/refman/8.0/en/json-table-functions.html)
- [MySQL 8.0 EXPLAIN](https://dev.mysql.com/doc/refman/8.0/en/explain.html)

需要精确版本结论时核对实际版本官方文档，不用其他 SQL 方言的解析结果替代 MySQL 证据。
