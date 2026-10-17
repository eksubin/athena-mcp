# Workflows

[[Home]] · [[API and MCP]] · [[Data and Authentication]]

## Profile

Sign in, visit /profile, set preferences, upload a resume, and review extracted facts. Maintain reusable application answers in the answer bank. Resume parsing produces structured facts for later use.

## Search and applications

Use search_jobs for ranked summaries and get_job for detail. Save a listing or call start_application to obtain the job, application record, and answer bank for a supervised browser flow. MCP does not itself fill external forms.

Statuses: saved, applied, pending, interview, offer, rejected. Manage applications at /dashboard or with MCP. Status updates place structures on the user's world plot. The /world page uses React Three Fiber/three.js; refresh for others' changes because Realtime is absent.

## Ingestion

The scheduled worker finds the latest HN monthly "Who is hiring?" thread via Algolia's public API, parses top-level comments, and upserts jobs with the service role. INTERVAL_SECONDS sets the interval; the documented default is daily. Failures are logged before the next interval.

LinkedIn and Twitter/X remain human-supervised browser workflows. linkedin_ingest.py only normalizes already captured data; it does not fetch pages or hold a browser session. POST /jobs supports listing import.

Parsing limits: LinkedIn salaries come from listing headers, hourly pay is omitted, and relative posting dates are approximate. HN free-form parsing is best-effort and misses some salary formats.

Sources: [worker README](../worker/README.md), [worker loop](../worker/athena_worker/main.py), [application routes](../backend/app/api/routes/applications.py).
