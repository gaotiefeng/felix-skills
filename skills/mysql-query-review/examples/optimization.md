# 合成示例：输入与参考输出

以下材料均为合成数据，可复制到聊天中试用。参考输出展示分析方式，不是每次审查都要套用的报告格式；均以只分析材料、不执行数据库操作为前提。

## 1. 检查语法

**输入**

> 使用 mysql-query-review，检查 MySQL 8.0 语句 `SELECT id, FROM users;`，说明错误并给出最小修复。

**参考输出**

`FROM` 前多了逗号，后面缺少选择表达式。删除该逗号：

```sql
SELECT id FROM users;
```

这是静态发现；表和字段是否存在仍需元数据或服务器校验。

## 2. 改进日期条件，复用已有索引

**输入**

> 使用 mysql-query-review，优化下面查询。目标为 MySQL 8.0 / InnoDB；created_at 为 DATETIME，日期参数与存储值采用同一业务时间口径。需要当天记录，保留排序及前 20 条限制。没有提供执行计划或耗时。

```sql
CREATE TABLE sample_events (
    id BIGINT NOT NULL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    status INT NOT NULL,
    created_at DATETIME NOT NULL,
    KEY idx_tenant_status_created (tenant_id, status, created_at)
) ENGINE=InnoDB;

SELECT id, created_at
FROM sample_events
WHERE tenant_id = 7
  AND status = 1
  AND DATE(created_at) = '2026-10-20'
ORDER BY created_at, id
LIMIT 20;
```

**参考输出**

可先把日期函数条件改为半开区间，使原始日期列条件可用于范围访问，并优先复用现有联合索引：

```sql
SELECT id, created_at
FROM sample_events
WHERE tenant_id = 7
  AND status = 1
  AND created_at >= '2026-10-20 00:00:00'
  AND created_at <  '2026-10-21 00:00:00'
ORDER BY created_at, id
LIMIT 20;
```

该改写基于给定的 DATETIME 类型及时间口径。InnoDB 二级索引携带主键，不需要仅为返回 id 再建一个追加 id 的近似索引。

下一步对比原查询与改写的 EXPLAIN，检查访问范围和估算行数；在相同数据上比较结果值、顺序以及日界记录。实际索引选择和提速幅度尚待目标环境验证。本次仅做静态分析。

## 3. 型号与单号组合筛选、分页及索引候选

**输入**

> 使用 mysql-query-review，审查下面 MySQL 8.0 / InnoDB 查询。保留 sort 的原排序方向，给出分页和索引建议。没有提供行数、频率或计划。

```sql
CREATE TABLE sample_lines (
    id BIGINT NOT NULL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    order_number VARCHAR(64) NOT NULL,
    model_id BIGINT NOT NULL,
    sort INT NOT NULL DEFAULT 0 COMMENT '排序',
    deleted BIT NOT NULL DEFAULT b'0',
    KEY idx_order (order_id),
    KEY idx_model (model_id)
) ENGINE=InnoDB;

SELECT id, sort
FROM sample_lines
WHERE model_id = 7
  AND order_number = 'SO007'
  AND deleted = b'0'
ORDER BY sort
LIMIT 20 OFFSET 20;
```

**参考输出**

静态阅读未发现明显语法问题。`ORDER BY sort` 是升序，同值行的顺序未确定；如需固定这些行的先后，可补充主键：

```sql
ORDER BY sort ASC, id ASC
LIMIT 20 OFFSET 20;
```

这细化了原来未规定的并列行顺序，分页中选中的并列记录也可能变化；不是把原结果按倒序重排，也不保证并发增删时 OFFSET 分页完全不偏移。

已有 idx_model 可能用于缩小筛选范围，不能因单号未索引就断言整条查询全表扫描。如果该组合是高频入口、现有访问量较大，可在测试环境比较候选：

```sql
-- 候选，审查时不执行
CREATE INDEX idx_model_order_deleted_sort
ON sample_lines (model_id, order_number, deleted, sort);
```

前三列对应等值过滤，sort 对应排序；InnoDB 携带主键，id 不机械重复追加。model_id 在前便于复用型号查询前缀；若主要入口是单号查询，应比较以单号开头的列序。新增索引会增加写入及空间成本，不直接删除已有索引。

下一步取得真实参数下的 EXPLAIN，检查访问路径、排序和访问量，再决定是否值得新增。当前没有依据标为严重性能缺陷；字段注释也不能证明 sort 仅在订单内递增。本次仅做静态分析。

## 4. 材料不完整时怎样反馈

**只有需求，没有语句**

输入：“帮我优化一下MySQL。”

参考输出：“请先贴需要审查的SQL；如果目前只有建表语句或执行计划，也可以先发其中一项，我会先分析已有材料。”此时不编写虚构的缺索引结论。

**SQL被省略**

输入：`SELECT id FROM users WHERE status = 1 AND [后面省略]`。

参考输出：“当前省略了AND之后的条件，无法判断完整语句或给出保留结果的改写。请贴完整SQL，包含实际WHERE、ORDER BY和LIMIT（若有）。目前只能检查已展示部分，不会删除AND后把片段当成最终查询。”

**名称与DDL不一致**

输入：完整DDL为 `users(id BIGINT PRIMARY KEY, display_name VARCHAR(64))`，SQL为 `SELECT nickname FROM users;`。

参考输出：“语句结构本身没有明显语法问题；按给定DDL，nickname未定义，会有名称解析问题。请确认这份DDL与实际查询环境一致。若你要取display_name，可以在确认字段含义后改名；我不会自动替换并称其为等价优化。”

**只给局部计划**

输入：`inner lookup actual time=0.010..0.020 rows=2 loops=1000`，问整条查询耗时。

参考输出：“该节点约累计输出2000行，不是物理读取量；局部节点不足以确定整条查询耗时。请补完整计划，保留根节点和层级；已有SQL也一起贴出，便于判断连接关系。本次只解释可见节点，没有运行查询。”

## 常见问题

**只有SQL，没有DDL或EXPLAIN，能用吗？**

可以先检查明显语法、版本前提和查询写法。需要核对字段或索引时再补对应表定义；实际访问路径及收益需要目标环境的计划/测量。简单语法修复不必先补齐所有资料。

**需要提供数据库账号或安装Python吗？**

本技能本身不需要。它通过宿主AI分析提供的材料，没有必需的运行脚本或数据库连接。静态审查不等于目标MySQL服务器已执行校验。

**建议中的CREATE INDEX可以直接在生产执行吗？**

它是候选，不是执行授权。先核对现有索引和查询负载，在获授权的测试环境验证结果、计划、写入/空间及建索引影响，再决定是否采用。

**为什么不能直接给出提速倍数？**

实际效果取决于数据、参数和负载。先给改写与验证步骤；只有在可比较条件下取得真实测量，才报告对应收益，不把计划估算当作实测。

## 示例的验证范围

既往本地临时 MySQL 8.4.0 核对过示例 1 的语法错误、示例 2 的日期边界和结果，以及与示例 3 查询形态一致的 2 万条合成数据测试：补主键后保留升序，反转方向改变分页，候选索引前后稳定分页及全部匹配结果一致。示例 3 的既往测试表还含其他单列索引，不是上方精简 DDL 的逐字实测。

这些是 SQL 行为核对，不是 MySQL 8.0 实测、模型独立行为评估或业务性能保证。参考输出没有连接数据库；实际使用时以目标版本、DDL、数据分布及授权的验证结果为准。
