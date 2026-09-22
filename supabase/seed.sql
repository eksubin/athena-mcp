-- Sample jobs for local development, so `search_jobs` returns something
-- before the Phase 3 ingestion worker exists. Safe to re-run.
insert into public.jobs (source, external_id, title, company, url, description, location, salary_min, salary_max, remote, easy_apply, posted_at)
values
  ('linkedin', 'seed-001', 'Senior Backend Engineer', 'Northwind Systems', 'https://example.com/jobs/seed-001', 'Own the payments API. Python/Postgres.', 'Remote', 150000, 190000, true, true, now() - interval '2 days'),
  ('linkedin', 'seed-002', 'Platform Engineer', 'Cedarbrook', 'https://example.com/jobs/seed-002', 'Build internal tooling on Kubernetes.', 'Austin, TX', 140000, 175000, false, true, now() - interval '1 day'),
  ('hn', 'seed-003', 'Founding Engineer', 'Fernway', 'https://example.com/jobs/seed-003', 'Early hire, full-stack, equity-heavy.', 'Remote', 120000, 160000, true, false, now() - interval '5 days'),
  ('linkedin', 'seed-004', 'Staff Software Engineer', 'Halcyon Labs', 'https://example.com/jobs/seed-004', 'Distributed systems, high scale.', 'New York, NY', 190000, 230000, false, true, now() - interval '3 hours'),
  ('twitter', 'seed-005', 'Backend Engineer (Contract)', 'Ridgeline', 'https://example.com/jobs/seed-005', '6-month contract, API work.', 'Remote', 90000, 120000, true, false, now() - interval '7 days')
on conflict (source, external_id) do nothing;
