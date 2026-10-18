"""Exercise every MCP tool over stdio against a real Athena deployment.

This is the executable half of CONTRACT.md: the only check that runs this
client and a backend together, so it is what you run after changing
either one. It talks to whatever deployment the environment points it at
— the local docker stack, or a hosted one over the network — and needs
two server-side secrets to mint a disposable account, so it is an
operator's tool, not something a user of the MCP ever runs.

    ATHENA_API_URL             default http://localhost:8000
    ATHENA_SUPABASE_URL        default http://localhost:8001
    SUPABASE_SERVICE_ROLE_KEY  required
    SUPABASE_JWT_SECRET        required

Against the local stack, the two secrets are in the Athena repository's
root .env. Run it with `uv run python scripts/smoke_test.py`.
"""
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import uuid

import httpx
import jwt

from athena_mcp import contract


def environment():
    """The deployment under test, from the environment alone — nothing
    here may assume a checkout of the Athena repository next door."""
    missing = [k for k in ('SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_JWT_SECRET') if not os.environ.get(k)]
    if missing:
        sys.exit(
            'smoke_test: set ' + ' and '.join(missing) + '.\n\n'
            'They are the deployment\'s own secrets (the Athena repository\'s root\n'
            '.env has them for the local docker stack) and are needed to create and\n'
            'delete the disposable account this check runs as.'
        )
    return (
        os.environ.get('ATHENA_API_URL', 'http://localhost:8000').rstrip('/'),
        os.environ.get('ATHENA_SUPABASE_URL', 'http://localhost:8001').rstrip('/'),
        os.environ['SUPABASE_SERVICE_ROLE_KEY'],
        os.environ['SUPABASE_JWT_SECRET'],
    )


def main():
    api_url, supabase_url, service_role_key, jwt_secret = environment()
    admin = httpx.Client(base_url=supabase_url, headers={
        'apikey': service_role_key,
        'Authorization': 'Bearer ' + service_role_key,
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
        token = jwt.encode({'sub': uid, 'aud': 'authenticated', 'role': 'authenticated'}, jwt_secret, algorithm='HS256')
        api = httpx.Client(base_url=api_url, headers={'Authorization': 'Bearer ' + token}, timeout=60)

        # The cross-repo contract, checked from the client's side: this
        # deployment must still speak a version this client can use.
        health = checked(api.get('/health'))
        assert isinstance(health.get('mcp_contract'), int), health
        assert health['mcp_contract_min'] <= contract.CONTRACT_VERSION <= health['mcp_contract'], (
            f'athena-mcp speaks contract {contract.CONTRACT_VERSION}; {api_url} speaks '
            f"{health['mcp_contract']} and supports {health['mcp_contract_min']} upward"
        )

        pat = checked(api.post('/tokens', json={'label': 'MCP smoke test'}))['token']
        job_id = checked(api.post('/jobs', json=[{'source': 'smoke-test', 'external_id': marker, 'title': 'MCP Engineer', 'company': 'Athena Test', 'url': 'https://example.com'}]))[0]['id']
        # Launched the way a desktop client launches it: this interpreter,
        # from a directory that has nothing of Athena in it, with the two
        # settings supplied as environment variables and no .env in reach.
        env = {**os.environ, 'ATHENA_TOKEN': pat, 'ATHENA_API_URL': api_url}
        process = subprocess.Popen([sys.executable, '-m', 'athena_mcp.server'], cwd=tempfile.gettempdir(), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
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

        print(f'PASS against {api_url}: API contract {health["mcp_contract"]} accepts this client '
              f'(contract {contract.CONTRACT_VERSION}), ten MCP tools, launch from an unrelated '
              'directory, workflow instructions, typed statuses, profile facts, review-only '
              'context, repeat-save preservation, one-call tracking with status, and listing '
              'links on every record')
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
