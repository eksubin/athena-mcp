"""Run inside the API container: python - < scripts/smoke_test.py.

Uses a disposable account and job; removes both, including resume files.
"""
import os
import secrets
import shutil
import uuid
from pathlib import Path

import httpx


def main():
    marker = uuid.uuid4().hex
    uid = job_id = None
    admin = httpx.Client(base_url=os.environ['SUPABASE_URL'], headers={
        'apikey': os.environ['SUPABASE_SERVICE_ROLE_KEY'],
        'Authorization': 'Bearer ' + os.environ['SUPABASE_SERVICE_ROLE_KEY'],
    }, timeout=30)

    def checked(response):
        assert response.is_success, f'{response.request.method} {response.request.url.path}: {response.status_code} {response.text}'
        return response.json() if response.content else None

    try:
        email, password = f'athena-smoke-{marker}@example.com', secrets.token_urlsafe(24)
        uid = checked(admin.post('/auth/v1/admin/users', json={
            'email': email, 'password': password, 'email_confirm': True,
        }))['id']
        session = checked(admin.post('/auth/v1/token?grant_type=password', json={'email': email, 'password': password}))
        api = httpx.Client(base_url='http://localhost:8000', headers={'Authorization': 'Bearer ' + session['access_token']}, timeout=60)
        checked(api.get('/health'))
        assert checked(api.get('/profile'))['id'] == uid
        assert checked(api.patch('/profile', json={'real_name': 'Smoke Test', 'preferences': {'remote': True}}))['real_name'] == 'Smoke Test'
        job_id = checked(api.post('/jobs', json=[{'source': 'smoke-test', 'external_id': marker, 'title': 'Python Engineer', 'company': 'Athena Test', 'url': 'https://example.com/job', 'remote': True}]))[0]['id']
        assert isinstance(checked(api.get('/jobs')), list)
        assert checked(api.get('/jobs/' + job_id))['id'] == job_id
        application = checked(api.post('/applications', json={'job_id': job_id}))
        for status in ('applied', 'pending', 'interview', 'offer', 'rejected'):
            assert checked(api.patch('/applications/' + application['id'], json={'status': status, 'note': 'smoke test'}))['status'] == status
        assert checked(api.get('/applications', params={'status': 'rejected'}))[0]['id'] == application['id']
        checked(api.post('/answers', json={'question': 'Test question?', 'answer': 'Test answer', 'sensitive': True}))
        assert checked(api.get('/answers'))[0]['sensitive']
        resume = checked(api.post('/resumes', files={'file': ('smoke.txt', b'Smoke Test\nsmoke@example.com\nPython, SQL', 'text/plain')}))
        assert resume['parsed_at']
        assert checked(api.get('/resumes'))
        assert checked(api.get('/resumes/' + resume['id'] + '/facts'))
        assert checked(api.get('/profile/facts'))
        assert any(p['user_id'] == uid for p in checked(api.get('/world/plots')))
        assert len([s for s in checked(api.get('/world/structures')) if s['user_id'] == uid]) == 6
        pat = checked(api.post('/tokens', json={'label': 'Smoke test'}))
        assert checked(api.get('/tokens'))
        assert checked(api.get('/profile', headers={'Authorization': 'Bearer ' + pat['token']}))['id'] == uid
        checked(api.delete('/tokens/' + pat['id']))
        assert api.get('/profile', headers={'Authorization': 'Bearer ' + pat['token']}).status_code == 401
        with httpx.Client(base_url='http://web:3000', timeout=60, follow_redirects=True) as web:
            checked(web.post('/auth/test-login', json={'email': email, 'password': password, 'action': 'in'}))
            for page in ('dashboard', 'profile', 'settings', 'world'):
                response = web.get('/' + page)
                assert response.status_code == 200 and response.url.path == '/' + page, f'{page}: {response.status_code} {response.url}'
                assert 'Internal Server Error' not in response.text
        print('PASS: authentication, profile, job import/search/detail, all application statuses, answers, resume/facts, world, PAT creation/use/revocation, and four authenticated web pages')
    finally:
        if uid:
            checked(admin.delete('/auth/v1/admin/users/' + uid))
            resume_dir = Path(os.environ.get('RESUME_STORAGE_DIR', '/data/resumes')) / uid
            if resume_dir.exists():
                shutil.rmtree(resume_dir)
        if job_id:
            checked(admin.delete('/rest/v1/jobs', params={'id': 'eq.' + job_id}))
        admin.close()


if __name__ == '__main__':
    main()
