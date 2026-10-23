import { McpServer } from '@modelcontextprotocol/server';
import { serveStdio } from '@modelcontextprotocol/server/stdio';
import * as z from 'zod';

const MAX_BYTES = 65536;
const Output = z.object({ order_id: z.string().min(1).max(64), status: z.string().min(1).max(100) });

function configuration() {
  const base = (process.env.API_BASE_URL ?? '').replace(/\/+$/, '');
  const token = process.env.API_TOKEN ?? '';
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password || url.search || url.hash) {
    throw new Error('API_BASE_URL must be an HTTP(S) URL without credentials, query or fragment');
  }
  if (!token || /[\r\n]/.test(token)) throw new Error('API_TOKEN is required and must not contain newlines');
  const timeout = Number(process.env.API_TIMEOUT_SECONDS ?? '5');
  if (!Number.isFinite(timeout) || timeout <= 0 || timeout > 30) throw new Error('API_TIMEOUT_SECONDS must be greater than 0 and at most 30');
  return { base, token, timeout };
}

class UpstreamError extends Error {}

async function readLimited(response: Response): Promise<string> {
  if (!response.body) throw new UpstreamError('INVALID_RESPONSE: 上游响应为空。');
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    for (;;) {
      const item = await reader.read();
      if (item.done) break;
      length += item.value.byteLength;
      if (length > MAX_BYTES) {
        await reader.cancel();
        throw new UpstreamError('RESPONSE_TOO_LARGE: 上游响应超过示例大小限制。');
      }
      chunks.push(item.value);
    }
  } finally { reader.releaseLock(); }
  return Buffer.concat(chunks).toString('utf8');
}

function createServer(settings: ReturnType<typeof configuration>) {
  const server = new McpServer({ name: 'rest-orders-example', version: '0.1.0' }, { capabilities: { tools: {} } });
  server.registerTool('get_order', {
    description: '按订单标识查询状态；只读取数据，不创建、修改或发送订单。',
    inputSchema: z.object({ order_id: z.string().min(1).max(64).regex(/^[A-Za-z0-9_-]+$/) }),
    outputSchema: Output,
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true }
  }, async ({ order_id }) => {
    const signal = AbortSignal.timeout(Math.ceil(settings.timeout * 1000));
    try {
      const response = await fetch(`${settings.base}/orders/${encodeURIComponent(order_id)}`, {
        headers: { Authorization: `Bearer ${settings.token}`, Accept: 'application/json' },
        signal, redirect: 'manual'
      });
      if (response.status !== 200) {
        await response.body?.cancel();
        const errors: Record<number, string> = {
          401: 'AUTH_FAILED: 上游认证失败，请检查API_TOKEN配置。',
          403: 'ACCESS_DENIED: 上游拒绝访问，请核对账号权限。',
          404: 'NOT_FOUND: 上游没有找到该订单。',
          429: 'RATE_LIMITED: 上游限流，请稍后重试。'
        };
        if (response.status >= 300 && response.status < 400) throw new UpstreamError('UPSTREAM_REDIRECT: 上游发生重定向，请核对固定API地址。');
        throw new UpstreamError(errors[response.status] ?? 'UPSTREAM_UNAVAILABLE: 上游返回异常状态，请稍后检查。');
      }
      if (!response.headers.get('content-type')?.toLowerCase().startsWith('application/json')) {
        await response.body?.cancel();
        throw new UpstreamError('INVALID_RESPONSE: 上游未返回JSON，请核对接口版本。');
      }
      let order: z.infer<typeof Output>;
      try {
        order = Output.parse(JSON.parse(await readLimited(response)));
        if (order.order_id !== order_id) throw new Error('response identifier mismatch');
      } catch (error) {
        if (error instanceof UpstreamError || signal.aborted) throw error;
        throw new UpstreamError('INVALID_RESPONSE: 上游数据不符合订单响应结构，请核对接口。');
      }
      return { content: [{ type: 'text', text: JSON.stringify(order) }], structuredContent: order };
    } catch (error) {
      const message = signal.aborted ? 'UPSTREAM_TIMEOUT: 上游请求超时，请稍后重试。'
        : error instanceof UpstreamError ? error.message : 'NETWORK_ERROR: 无法连接上游，请检查地址与网络。';
      return { isError: true, content: [{ type: 'text', text: message }] };
    }
  });
  return server;
}

try {
  const settings = configuration();
  serveStdio(() => createServer(settings), { onerror: () => console.error('MCP transport error') });
} catch (error) {
  console.error('Configuration error:', error instanceof Error ? error.message : 'Invalid configuration');
  process.exitCode = 1;
}
