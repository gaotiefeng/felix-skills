"""Protocol-level smoke tests for the bundled get_order examples, using a local fake API."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from jsonschema import validate as validate_schema
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from mock_api import MOCK_TOKEN, SECRET_MARKER, create_mock


async def check(target, project, mode, node_command):
    if target == 'python':
        command, args = sys.executable, ['-B', str(project / 'server.py')]
    else:
        command, args = node_command, [str(project / 'dist/server.js')]
    if not Path(args[-1]).is_file():
        raise ValueError('Server entry not found; copy/build the selected template first')
    api, requests = create_mock()
    worker = threading.Thread(target=api.serve_forever, daemon=True)
    worker.start()
    env = {'API_BASE_URL': f'http://127.0.0.1:{api.server_port}', 'API_TOKEN': MOCK_TOKEN,
           'API_TIMEOUT_SECONDS': '0.25', 'PYTHONDONTWRITEBYTECODE': '1'}
    checks = []

    def record(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append({'name': name, 'passed': True})

    try:
        async with Client(StdioServerParameters(command=command, args=args, env=env, cwd=project),
                          mode=mode, read_timeout_seconds=5) as client:
            tools = (await client.list_tools()).tools
            record('tool discovery and schema', len(tools) == 1 and tools[0].name == 'get_order'
                   and tools[0].input_schema.get('required') == ['order_id'] and tools[0].output_schema is not None)
            protocol = client.protocol_version
            result = await client.call_tool('get_order', {'order_id': 'TEST001'})
            record('successful structured response', not result.is_error and result.structured_content ==
                   {'order_id': 'TEST001', 'status': 'in_transit'})
            validate_schema(result.structured_content, tools[0].output_schema)
            for label, arguments in [('missing parameter', {}), ('wrong type', {'order_id': 123}),
                                     ('invalid path characters', {'order_id': '../secret'})]:
                before = len(requests)
                result = await client.call_tool('get_order', arguments)
                record(label + ' rejected before upstream', result.is_error and len(requests) == before)
            for identifier, expected in [('AUTH', 'AUTH_FAILED'), ('FORBIDDEN', 'ACCESS_DENIED'),
                    ('MISSING', 'NOT_FOUND'), ('LIMITED', 'RATE_LIMITED'), ('BROKEN', 'UPSTREAM_UNAVAILABLE'),
                    ('BADJSON', 'INVALID_RESPONSE'), ('BADSHAPE', 'INVALID_RESPONSE'),
                    ('WRONGID', 'INVALID_RESPONSE'), ('WRONGTYPE', 'INVALID_RESPONSE'),
                    ('TOOBIG', 'RESPONSE_TOO_LARGE'), ('REDIRECT', 'UPSTREAM_REDIRECT'),
                    ('SLOW', 'UPSTREAM_TIMEOUT')]:
                before = len(requests)
                result = await client.call_tool('get_order', {'order_id': identifier})
                text = '\n'.join(getattr(c, 'text', '') for c in result.content)
                record(identifier + ' maps to tool error without retry or body leak', result.is_error
                       and expected in text and SECRET_MARKER not in text and MOCK_TOKEN not in text
                       and len(requests) == before + 1)
            result = await client.call_tool('get_order', {'order_id': 'EXTRA'})
            record('success after errors and allowlisted output fields', not result.is_error
                   and result.structured_content == {'order_id': 'EXTRA', 'status': 'in_transit'}
                   and SECRET_MARKER not in json.dumps(result.model_dump()))
            record('redirect never followed', '/should-not-follow' not in requests)
        bad_env = {**os.environ, **env, 'API_TOKEN': ''}
        bad = subprocess.run([command, *args], env=bad_env, cwd=project, input='',
                             capture_output=True, text=True, timeout=10)
        record('missing credential fails clearly on stderr', bad.returncode != 0
               and 'API_TOKEN' in bad.stderr and not bad.stdout)
        api.shutdown()
        api.server_close()
        worker.join(timeout=2)
        async with Client(StdioServerParameters(command=command, args=args, env=env, cwd=project),
                          mode=mode, read_timeout_seconds=5) as client:
            await client.list_tools()
            result = await client.call_tool('get_order', {'order_id': 'TEST001'})
            text = '\n'.join(getattr(c, 'text', '') for c in result.content)
            record('connection failure maps to safe tool error', result.is_error and 'NETWORK_ERROR' in text)
    finally:
        api.shutdown()
        api.server_close()
        worker.join(timeout=2)
    return {'target': target, 'mode': mode, 'protocol': protocol, 'checks': checks,
            'passed': len(checks), 'api_request_count': len(requests),
            'scope': 'bundled read-only stdio examples and loopback mock API; no live service or GUI host tested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['python', 'typescript'], required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--mode', choices=['auto', 'legacy'], default='auto')
    parser.add_argument('--node-command', default='node')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = asyncio.run(check(args.target, args.project.resolve(), args.mode, args.node_command))
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as f:
            f.write(content)
    print(content)


if __name__ == '__main__':
    main()
