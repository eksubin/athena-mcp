import json
import unittest

import httpx

from athena_mcp.client import AthenaClient


class ClientTests(unittest.TestCase):
    def client(self, handler):
        client = AthenaClient.__new__(AthenaClient)
        client._http = httpx.Client(base_url='http://athena.test', transport=httpx.MockTransport(handler))
        self.addCleanup(client._http.close)
        return client

    def test_profile_includes_extracted_facts_and_confidence(self):
        def handle(request):
            data = [{'key': 'email', 'value': 'qa@example.com', 'confidence': .9}] if request.url.path == '/profile/facts' else {'id': 'user'}
            return httpx.Response(200, json=data)
        result = self.client(handle).get_profile()
        self.assertEqual(result['id'], 'user')
        self.assertEqual(result['facts'][0]['confidence'], .9)

    def test_track_records_the_listing_and_its_status_in_one_call(self):
        def handle(request):
            self.assertEqual(request.url.path, '/applications/track')
            body = json.loads(request.content)
            self.assertEqual(body['status'], 'applied')
            self.assertEqual(body['title'], 'Research Scientist')
            self.assertEqual(body['salary_min'], 90000)
            return httpx.Response(200, json={'job': {'id': 'job'}, 'created': True})
        result = self.client(handle).track_job(
            'https://careers.example.com/roles/7', 'Research Scientist', 'University',
            status='applied', salary_min=90000,
        )
        self.assertEqual(result['job']['id'], 'job')

    def test_track_omits_fields_the_caller_did_not_observe(self):
        """A field sent as null would blank out what Athena already holds;
        an unobserved field must simply not be sent."""
        def handle(request):
            body = json.loads(request.content)
            self.assertNotIn('description', body)
            self.assertNotIn('salary_min', body)
            self.assertEqual(body['location'], 'Berlin')
            return httpx.Response(200, json={})
        self.client(handle).track_job(
            'https://careers.example.com/roles/7', 'Scientist', 'University',
            location='Berlin', description=None, salary_min=None,
        )

    def test_track_refuses_a_listing_with_no_observed_title_or_company(self):
        def handle(request):
            self.fail('An invented listing must not reach the API')
        client = self.client(handle)
        with self.assertRaises(ValueError):
            client.track_job('https://careers.example.com/roles/7', '  ', 'University')
        with self.assertRaises(ValueError):
            client.track_job('https://careers.example.com/roles/7', 'Scientist', '')

    def test_linkedin_import_canonicalizes_the_url_and_tracks_it(self):
        def handle(request):
            self.assertEqual(request.url.path, '/applications/track')
            body = json.loads(request.content)
            self.assertEqual(body['url'], 'https://www.linkedin.com/jobs/view/123/')
            self.assertEqual(body['title'], 'Research Scientist')
            self.assertEqual(body['status'], 'saved')
            return httpx.Response(200, json={'job': {'id': 'job'}})
        self.assertEqual(
            self.client(handle).import_linkedin_job(
                'https://www.linkedin.com/jobs/view/123/?tracking=abc', 'Research Scientist', 'University'
            ),
            {'job': {'id': 'job'}},
        )

    def test_import_rejects_unrelated_or_non_job_urls_before_http(self):
        def handle(request):
            self.fail('Invalid URL must not reach the API')
        client = self.client(handle)
        for url in ('https://linkedin.com.example.org/jobs/view/123/', 'https://www.linkedin.com/in/person/', 'http://www.linkedin.com/jobs/view/123/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                client.import_linkedin_job(url, 'Scientist', 'University')

    def test_saving_a_job_relies_on_the_idempotent_endpoint(self):
        """POST /applications returns the existing record for an
        already-saved job, so the client does not scan the queue first."""
        requests = []

        def handle(request):
            requests.append((request.method, request.url.path))
            return httpx.Response(200, json={'id': 'app', 'job_id': 'job', 'status': 'interview'})
        self.assertEqual(self.client(handle).save_job('job')['status'], 'interview')
        self.assertEqual(requests, [('POST', '/applications')])


if __name__ == '__main__':
    unittest.main()
