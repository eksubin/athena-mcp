"""Exercise every MCP tool over stdio using a disposable local account.

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
    email = f'athena-mcp-{marker}@example.com'
    uid = job_id = imported_job_id = tracked_job_id = process = watchdog = None

    def checked(response):
        response.raise_for_status()
        return response.json() if response.content else None

    try:
        # Athena is invite-only: a database trigger refuses any account
        # whose address isn't on the allowlist, including one created
        # through GoTrue's admin API. Allowlist the disposable address
        # first, and take the row away again in the cleanup below.
        checked(admin.post('/rest/v1/invites', json={'email': email, 'note': 'MCP smoke test'}))
        uid = checked(admin.post('/auth/v1/admin/users', json={
            'email': email,
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
        assert len(tools) == 10
        assert tools['get_profile']['annotations']['readOnlyHint']
        assert 'applied' in tools['update_status']['inputSchema']['properties']['status']['enum']
        # The listing fields an agent can fill in from a page it is reading.
        track_fields = set(tools['track_job']['inputSchema']['properties'])
        assert {'url', 'title', 'company', 'status', 'location', 'description',
                'salary_min', 'salary_max', 'remote', 'easy_apply',
                'posted_at', 'note'} <= track_fields, track_fields
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
        imported_result = imported.get('structuredContent') or json.loads(imported['content'][0]['text'])
        imported_job_id = imported_result['job']['id']
        # Registering a listing now also records where the user stands on
        # it, rather than leaving a catalog entry nobody is tracking.
        assert imported_result['application']['status'] == 'saved', imported_result
        checked(api.post('/jobs', json=[{'source': 'linkedin', 'external_id': external_id,
            'url': import_args['url'], 'title': import_args['title'], 'company': 'Athena QA',
            'description': 'Existing detailed listing', 'remote': True}]))
        request(22, 'tools/call', {'name': 'import_linkedin_job', 'arguments': import_args})
        retained = checked(api.get('/jobs/' + imported_job_id))
        assert retained['description'] == 'Existing detailed listing' and retained['remote']

        # track_job: one call records an arbitrary listing and its status,
        # with no prior import, and repeats update rather than duplicate.
        track_args = {
            'url': 'https://careers.example.com/roles/' + marker + '?utm_source=smoke',
            'title': 'Tracked in one call', 'company': 'Athena QA',
            'status': 'applied', 'location': 'Remote', 'salary_min': 90000,
            'description': 'Observed from the listing page.',
        }
        tracked = request(23, 'tools/call', {'name': 'track_job', 'arguments': track_args})
        tracked_result = tracked.get('structuredContent') or json.loads(tracked['content'][0]['text'])
        tracked_job_id = tracked_result['job']['id']
        assert tracked_result['created'] and tracked_result['status_changed'], tracked_result
        assert tracked_result['application']['status'] == 'applied', tracked_result
        assert tracked_result['job']['url'].startswith('https://careers.example.com/'), tracked_result

        again = request(24, 'tools/call', {'name': 'track_job', 'arguments': {
            'url': 'https://careers.example.com/roles/' + marker,
            'title': 'Tracked in one call', 'company': 'Athena QA', 'status': 'interview',
        }})
        again_result = again.get('structuredContent') or json.loads(again['content'][0]['text'])
        assert again_result['job']['id'] == tracked_job_id, 'tracking the same link made a second job'
        assert not again_result['created'] and again_result['status_changed']
        assert again_result['job']['salary_min'] == 90000, 'an omitted field overwrote a stored one'

        # Every record an agent reads back carries the link, so reporting
        # on the queue needs no extra job lookups.
        queue = request(25, 'tools/call', {'name': 'get_queue', 'arguments': {'status': 'interview'}})
        queue_rows = (queue.get('structuredContent') or {}).get('result') or [
            json.loads(block['text']) for block in queue['content']
        ]
        assert any(row['job_id'] == tracked_job_id and row['job']['url'] for row in queue_rows), queue_rows
        assert all(job['url'] for job in checked(api.get('/jobs', params={'limit': 5})))

        print('PASS: ten MCP tools, launch from repository root, workflow instructions, typed statuses, profile facts, review-only context, repeat-save preservation, one-call tracking with status, and listing links on every record')
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
        if tracked_job_id:
            checked(admin.delete('/rest/v1/jobs', params={'id': 'eq.' + tracked_job_id}))
        checked(admin.delete('/rest/v1/invites', params={'email': 'eq.' + email}))
        admin.close()


if __name__ == '__main__':
    main()
