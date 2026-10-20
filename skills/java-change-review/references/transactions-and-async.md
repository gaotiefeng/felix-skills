# 事务与异步：从调用路径确认行为

## 事务是否生效

先确认代理模式、实际调用入口和事务管理器。默认 Spring proxy 模式的同实例自调用不会经过该事务拦截器，但外层可能已有事务，或项目使用 AspectJ。发现 self-invocation 后要解释具体丢失了哪种事务语义，不能一律报告“完全没有事务”。

方法可见性与代理支持随 Spring 版本及代理类型变化，不使用“所有非 public 方法永远失效”这类笼统规则。

默认回滚规则与项目配置都要查：受检异常、catch 后正常返回、rollbackFor、全局规则或 rollback-only 都会影响结果。不要仅看异常类就判断一定提交或回滚。

## 事务与外部操作

数据库事务通常不能回滚已经发出的 HTTP 消息。检查外部操作与数据库提交的顺序、失败补偿和业务约定；如果一致性要求并不明确，先问或标记待确认。

提交后回调能调整发送时机，但不保证进程崩溃后消息一定投递。若需求是可靠投递，评估持久化 outbox 等机制，不把 afterCommit 当作必达方案。

长事务内调用慢服务可能长期持有连接，但需要确认在调用前已借出连接、事务范围与超时。单纯看到 @Transactional 内有 HTTP，不应直接声称当前发生了连接池耗尽。

## 异步线程

命令式线程绑定事务一般不会自动传播到新线程；还要核对调用是否真的异步、实际 executor 和异步方法自身事务边界。Reactive 事务使用不同上下文机制，遇到时按实际版本和链路检查。

MDC 或 TTL 传播不等于数据库事务传播。异步失败可能发生在调用方返回之后，检查 Future/CompletionStage 的观察与错误处理，以及 void 异步异常处理；不能假定外层 try/catch 能捕获后台异常。

## 官方参考

- [Spring @Transactional 说明](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)

根据项目实际版本核对默认行为与可配置项。
