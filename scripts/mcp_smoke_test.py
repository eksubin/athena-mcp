"""Exercise all nine MCP tools over stdio using a disposable local account.

Run from the repository root with mcp/.venv/Scripts/python scripts/mcp_smoke_test.py.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
import uuid

import httpx
from dotenv import dotenv_values


def main():
    root = Path(__file__).resolve().parents[1]
    config = dotenv_values(root / '.env')
    admin = httpx.Client(base_url='http://localhost:8001', headers={
        'apikey': config['SUPABASE_SERVICE_ROLE_KEY'],
        'Authorization': 'Bearer ' + config['SUPABASE_SERVICE_ROLE_KEY'],
    }, timeout=30)
    marker = uuid.uuid4().hex
    uid = job_id = imported_job_id = process = watchdog = None

    def checked(response):
        response.raise_for_status()
        return response.json() if response.content else None

    try:
        uid = checked(admin.post('/auth/v1/admin/users', json={
            'email': f'athena-mcp-{marker}@example.com',
            'password': secrets.token_urlsafe(24), 'email_confirm': True,
        }))['id']
        import jwt
        token = jwt.encode({'sub': uid, 'aud': 'authenticated', 'role': 'authenticated'}, config['SUPABASE_JWT_SECRET'], algorithm='HS256')
        api = httpx.Client(base_url='http://localhost:8000', headers={'Authorization': 'Bearer ' + token}, timeout=60)
        pat = checked(api.post('/tokens', json={'label': 'MCP smoke test'}))['token']
        job_id = checked(api.post('/jobs', json=[{'source': 'smoke-test', 'external_id': marker, 'title': 'MCP Engineer', 'company': 'Athena Test', 'url': 'https://example.com'}]))[0]['id']
        env = {**os.environ, 'ATHENA_TOKEN': pat, 'ATHENA_API_URL': 'http://localhost:8000'}
        process = subprocess.Popen([str(root / 'mcp/.venv/Scripts/python.exe'), '-m', 'athena_mcp.server'], cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        watchdog = threading.Timer(90, process.kill)
        watchdog.start()

        def request(number, method, params):
            process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': number, 'method': method, 'params': params}) + '\n')
            process.stdin.flush()
            while True:
                line = process.stdout.readline()
                assert line, 'MCP server exited unexpectedly'
                response = json.loads(line)
                if response.get('id') == number:
                    assert 'error' not in response, response
                    result = response['result']
                    assert not result.get('isError'), result
                    return result

        initialized = request(1, 'initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'athena-smoke', 'version': '1.0'}})
        assert 'review-only' in initialized['instructions']
        process.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        process.stdin.flush()
        tools = {t['name']: t for t in request(2, 'tools/list', {})['tools']}
        assert len(tools) == 9
        assert tools['get_profile']['annotations']['readOnlyHint']
        assert 'applied' in tools['update_status']['inputSchema']['properties']['status']['enum']
        calls = [('get_profile', {}), ('search_jobs', {'limit': 2}), ('get_job', {'job_id': job_id}), ('save_job', {'job_id': job_id}), ('record_answer', {'question': 'MCP test?', 'answer': 'Yes'}), ('start_application', {'job_id': job_id}), ('update_status', {'job_id': job_id, 'status': 'interview'}), ('get_queue', {'status': 'interview'})]
        for number, (name, arguments) in enumerate(calls, 3):
            result = request(number, 'tools/call', {'name': name, 'arguments': arguments})
            if name == 'start_application':
                context = result.get('structuredContent') or json.loads(result['content'][0]['text'])
                assert context['submitted'] is False
                assert context['application']['status'] == 'saved'
                assert 'facts' in context['profile']
        request(20, 'tools/call', {'name': 'save_job', 'arguments': {'job_id': job_id}})
        applications = checked(api.get('/applications'))
        assert len(applications) == 1 and applications[0]['status'] == 'interview'
        external_id = str(uuid.uuid4().int)
        import_args = {
            'url': 'https://www.linkedin.com/jobs/view/' + external_id + '/',
            'title': 'Disposable MCP integration test', 'company': 'Athena QA',
        }
        imported = request(21, 'tools/call', {'name': 'import_linkedin_job', 'arguments': import_args})
        imported_job_id = (imported.get('structuredContent') or json.loads(imported['content'][0]['text']))['id']
        checked(api.post('/jobs', json=[{'source': 'linkedin', 'external_id': external_id,
            'url': import_args['url'], 'title': import_args['title'], 'company': 'Athena QA',
            'description': 'Existing detailed listing', 'remote': True}]))
        request(22, 'tools/call', {'name': 'import_linkedin_job', 'arguments': import_args})
        retained = checked(api.get('/jobs/' + imported_job_id))
        assert retained['description'] == 'Existing detailed listing' and retained['remote']
        print('PASS: nine MCP tools, launch from repository root, workflow instructions, typed statuses, profile facts, review-only context, and repeat-save preservation')
    finally:
        if watchdog:
            watchdog.cancel()
        if process:
            process.terminate()
            process.wait(timeout=10)
        if uid:
            checked(admin.delete('/auth/v1/admin/users/' + uid))
        if job_id:
            checked(admin.delete('/rest/v1/jobs', params={'id': 'eq.' + job_id}))
        if imported_job_id:
            checked(admin.delete('/rest/v1/jobs', params={'id': 'eq.' + imported_job_id}))
        admin.close()


if __name__ == '__main__':
    main()
