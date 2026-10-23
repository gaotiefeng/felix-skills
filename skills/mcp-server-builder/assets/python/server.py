"""Read-only stdio MCP example. Adapt the explicit API contract for your service."""
import json
import logging
import math
import os
import socket
import sys
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, ValidationError

MAX_BYTES = 65536


def configuration():
    base = os.environ.get('API_BASE_URL', '').rstrip('/')
    token = os.environ.get('API_TOKEN', '')
    parsed = urlsplit(base)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('API_BASE_URL must be an HTTP(S) URL without credentials, query or fragment')
    if not token or '\r' in token or '\n' in token:
        raise ValueError('API_TOKEN is required and must not contain newlines')
    timeout = float(os.environ.get('API_TIMEOUT_SECONDS', '5'))
    if not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError('API_TIMEOUT_SECONDS must be greater than 0 and at most 30')
    return base, token, timeout


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OrderResult(BaseModel):
    order_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    status: Annotated[str, Field(strict=True, min_length=1, max_length=100)]


def create_server(base, token, timeout):
    mcp = MCPServer('rest-orders-example')
    opener = build_opener(NoRedirect())

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                         idempotent_hint=True, open_world_hint=True))
    def get_order(order_id: Annotated[str, Field(strict=True, min_length=1, max_length=64,
                                                pattern=r'^[A-Za-z0-9_-]+$')]) -> OrderResult:
        """按订单标识查询状态；只读取数据，不创建、修改或发送订单。"""
        request = Request(f'{base}/orders/{quote(order_id, safe="")}',
                          headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ToolError('UPSTREAM_STATUS: 上游响应状态不符合接口约定。')
                if response.headers.get_content_type() != 'application/json':
                    raise ToolError('INVALID_RESPONSE: 上游未返回JSON，请核对接口版本。')
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ToolError('RESPONSE_TOO_LARGE: 上游响应超过示例大小限制。')
        except HTTPError as exc:
            errors = {401: 'AUTH_FAILED: 上游认证失败，请检查API_TOKEN配置。',
                      403: 'ACCESS_DENIED: 上游拒绝访问，请核对账号权限。',
                      404: 'NOT_FOUND: 上游没有找到该订单。',
                      429: 'RATE_LIMITED: 上游限流，请稍后重试。'}
            message = errors.get(exc.code, 'UPSTREAM_UNAVAILABLE: 上游返回异常状态，请稍后检查。')
            if 300 <= exc.code < 400:
                message = 'UPSTREAM_REDIRECT: 上游发生重定向，请核对固定API地址。'
            exc.close()
            raise ToolError(message) from None
        except (TimeoutError, socket.timeout):
            raise ToolError('UPSTREAM_TIMEOUT: 上游请求超时，请稍后重试。') from None
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise ToolError('UPSTREAM_TIMEOUT: 上游请求超时，请稍后重试。') from None
            raise ToolError('NETWORK_ERROR: 无法连接上游，请检查地址与网络。') from None
        try:
            raw = json.loads(body)
            order = OrderResult.model_validate(raw)
            if order.order_id != order_id:
                raise ValueError('response identifier mismatch')
            return order
        except (ValueError, UnicodeError, ValidationError):
            raise ToolError('INVALID_RESPONSE: 上游数据不符合订单响应结构，请核对接口。') from None

    return mcp


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    try:
        settings = configuration()
    except ValueError as exc:
        raise SystemExit(f'Configuration error: {exc}')
    create_server(*settings).run(transport='stdio')
