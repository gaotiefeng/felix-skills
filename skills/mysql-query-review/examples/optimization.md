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

## 示例的验证范围

既往本地临时 MySQL 8.4.0 核对过示例 1 的语法错误、示例 2 的日期边界和结果，以及与示例 3 查询形态一致的 2 万条合成数据测试：补主键后保留升序，反转方向改变分页，候选索引前后稳定分页及全部匹配结果一致。示例 3 的既往测试表还含其他单列索引，不是上方精简 DDL 的逐字实测。

这些是 SQL 行为核对，不是 MySQL 8.0 实测、模型独立行为评估或业务性能保证。参考输出没有连接数据库；实际使用时以目标版本、DDL、数据分布及授权的验证结果为准。
