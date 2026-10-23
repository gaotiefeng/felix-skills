# Python 路径

内置模板位于 `assets/python/`。开发时复制到用户的新项目目录，再按实际接口修改；不要把业务密钥或项目数据写回技能包。

## 已固定的基线

- 项目要求 Python 3.11+；本机验证的具体版本见交付测试记录，不推定其他系统都通过。
- 官方 SDK `mcp==2.3.0`，使用 `from mcp.server import MCPServer`。
- 参数使用类型注解与 Pydantic Field，返回 Pydantic 模型形成输出 schema。预期业务失败抛 `mcp.server.mcpserver.exceptions.ToolError`，由SDK转成工具失败结果。
- stdio 由 SDK `.run(transport='stdio')` 启动，不自行维护协议帧或重复实现初始化。SDK负责版本兼容；不要把v1的FastMCP导入路径混进该模板。

## 创建与运行

复制模板后，在项目目录创建独立环境，安装 `requirements.lock` 中的测试基线依赖；需要重新解析依赖时以 `pyproject.toml` 为直接依赖来源，更新锁定记录并复测。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

`assets/.env.example` 只列出所需变量，不自动加载。通过终端或客户端环境传入 `API_BASE_URL`、`API_TOKEN`，可选 `API_TIMEOUT_SECONDS`（默认5秒，允许0到30秒之间且不含0）。凭证不作为工具参数交给模型。

这是现成Bearer Token模板，没有内置账号登录、租户、业务码判断或TOML加载。需要这些能力时按[接口接入与边界](api-integration.md)适配客户端和私有配置，再为该契约改写测试；不要将另一个项目的真实登录配置复制进模板。

使用项目虚拟环境中Python的绝对路径启动项目的 `server.py`。进入stdio后没有普通交互提示属正常现象；用MCP客户端发现/调用工具验证。业务日志只能写stderr。

## 适配真实API

示例只读 `GET /orders/{order_id}`，要求200 JSON包含同一 `order_id` 与非空 `status`，返回只保留这两项。需要不同字段、分页或路径时，同时修改参数、上游请求、响应模型和测试，不能只改函数名。

模板禁止自动跟随重定向，响应上限64KiB；这些是示例的实现选择，不是MCP统一规定。按目标接口调整并保留限额与测试。当前使用标准库同步HTTP，SDK在工作线程中运行同步工具；有高并发/取消要求时改为有生命周期管理的异步客户端并验证取消与资源释放。

官方依据：[Python SDK](https://py.sdk.modelcontextprotocol.io/)、[版本迁移说明](https://py.sdk.modelcontextprotocol.io/migration/)。网页和依赖要求可能变化，新增项目时重新核对，不盲目升级现有项目。
