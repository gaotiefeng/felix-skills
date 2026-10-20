# 内存异常与进程退出

## 先区分退出原因

- JVM 抛出的 OutOfMemoryError：读取完整异常类型、时间和上下文，区分 heap、metaspace、直接内存或无法创建线程等方向。
- 内核或容器 OOM kill：需要内核日志、容器事件或 cgroup 内存证据，核对被杀 PID 与实例。
- 退出码 137：说明常见约定下收到 SIGKILL，单独不能证明 OOM；人为 kill 或超时强杀也可能发生。

启用 HeapDumpOnOutOfMemoryError 不保证所有类型 OOM 都有 heap dump；OS 强杀时 JVM 通常来不及生成。也检查空间、权限和对应错误类型，不能因为没有 dump 就排除内存事故。

## 内存量要用对

Xmx 是堆上限，不是进程 RSS 或容器总内存上限。线程栈、元数据、代码缓存、直接内存、GC 与本地库都可能占内存。RSS 大于 Xmx 不等于 heap 泄漏。

堆使用上升应结合 GC 后存活量、负载和时间趋势；一次 Old 区较高不能证明泄漏。NMT 可辅助分析 HotSpot 管理的 native memory，但不覆盖所有第三方分配，也不能要求 NMT 数值精确等于 RSS。未启用时不要假定运行中能无代价补齐历史。

线程编号很大只说明累计创建历史。核对 live threads、线程栈与系统线程数量，再讨论本地内存压力。虚拟线程场景不能直接套用平台线程的“一线程一份固定原生栈”估算。

## 取证优先级

先使用已有监控、GC 日志、容器事件与启动参数。需要新采样时，用目标 JDK 的 `jcmd <pid> help <command>` 查支持情况和影响，确认进程所属用户与容器 PID 命名空间。

Thread.print 可产生暂停，GC.class_histogram 和 GC.heap_dump 可能高影响、触发 GC 或生成大文件；不能因为它们“只是诊断”就直接在线上运行。转储包含业务数据，生成前检查空间和访问限制。

止损方案应基于容量预算：内存、并发、数据量和同机服务相互关联。简单扩大 Xmx 可能加剧容器/主机内存压力；缩小堆也可能增加 GC，需给出验证指标。

## 参考

- [JDK 17 jcmd 命令与影响说明](https://docs.oracle.com/en/java/javase/17/docs/specs/man/jcmd.html)

用户提供的版本与环境优先，必要时查对应版本官方文档。
