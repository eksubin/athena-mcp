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

    def test_import_strips_tracking_and_preserves_observed_title(self):
        def handle(request):
            import json
            row = json.loads(request.content)[0]
            self.assertEqual(row['url'], 'https://www.linkedin.com/jobs/view/123/')
            self.assertEqual(row['external_id'], '123')
            self.assertEqual(row['title'], 'Research Scientist')
            return httpx.Response(201, json=[{'id': 'job'}])
        self.assertEqual(self.client(handle).import_linkedin_job('https://www.linkedin.com/jobs/view/123/?tracking=abc', 'Research Scientist', 'University'), {'id': 'job'})

    def test_import_rejects_unrelated_or_non_job_urls_before_http(self):
        def handle(request):
            self.fail('Invalid URL must not reach the API')
        client = self.client(handle)
        for url in ('https://linkedin.com.example.org/jobs/view/123/', 'https://www.linkedin.com/in/person/', 'http://www.linkedin.com/jobs/view/123/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                client.import_linkedin_job(url, 'Scientist', 'University')

    def test_saving_existing_application_does_not_reset_status(self):
        def handle(request):
            self.assertEqual(request.method, 'GET')
            return httpx.Response(200, json=[{'id': 'app', 'job_id': 'job', 'status': 'interview'}])
        self.assertEqual(self.client(handle).save_job('job')['status'], 'interview')


if __name__ == '__main__':
    unittest.main()
