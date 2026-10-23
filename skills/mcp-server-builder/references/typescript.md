# Node.js / TypeScript 路径

内置模板位于 `assets/typescript/`，先复制到用户项目目录。模板使用ESM、Node.js20+，官方 `@modelcontextprotocol/server==2.3.1`，直接依赖Zod并附带package-lock.json；固定版本是测试起点，不代表永远最新。

## 安装、构建与启动

在项目目录执行：

```bash
npm ci
npm run build
npm start
```

客户端启动时使用Node可执行文件绝对路径和项目 `dist/server.js` 的绝对路径；`npm start` 适合手动运行，客户端配置优先直接调用node入口以避免额外输出。先提供环境变量API_BASE_URL、API_TOKEN，可选API_TIMEOUT_SECONDS；`.env.example`不自动加载。

`src/server.ts` 用 `McpServer.registerTool` 和 `z.object` 定义输入/输出；成功返回content与structuredContent，预期上游失败返回isError=true。v2使用 `serveStdio` 服务工厂，不把v1单包 `@modelcontextprotocol/sdk` 的示例直接拼进该项目。

模板仅接收现成Bearer Token，没有内置账号登录、租户或业务码判断。需要这些能力时按[接口接入与边界](api-integration.md)适配API客户端和配置，并用新契约测试，不能只换工具名称就宣称接通。

## 修改与核对

- 保持类型、schema、上游参数和输出字段一致，别用 `as any` 绕过类型问题。
- fetch显式设置超时、拒绝自动跟随重定向，读取有大小限制，只返回约定字段；示例不自动重试。
- 修改API路径、鉴权或字段后，用相应模拟响应重新验证。上游报错正文不直接返回模型；stdio业务日志用console.error，不用console.log。
- lockfile更新必须对应package.json；安装失败先说明具体缺依赖/版本，不删除锁文件或退回其他SDK主版本后继续宣称原基线通过。

SDK不同主版本的包名和API不同。核对[官方仓库与文档入口](https://github.com/modelcontextprotocol/typescript-sdk)及[stdio服务入口源码](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/server/src/server/serveStdio.ts)，以实际安装包导出和类型检查为准。
