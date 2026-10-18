# Workflows

[[Home]] · [[API and MCP]] · [[Data and Authentication]] · [[Invites and Administration]]

## Joining

Athena is invite-only. An existing member adds an address from /profile, or an
administrator adds it from /admin; that address can then create its own
account. Nothing is emailed. An uninvited address is refused at sign-up with an
invite-only message, and an account whose access was withdrawn is sent back to
the login page. See [[Invites and Administration]].

## Profile

Sign in and visit /profile. Choose the username and the avatar other people
see in the shared world — both can be changed at any time, and neither is
your real name. Then set preferences, upload a resume, and review extracted
facts. Maintain reusable application answers in the answer bank. Resume parsing produces structured facts for later use.

## Search and applications

Use search_jobs for ranked summaries and get_job for detail. Save a listing or call start_application to obtain the job, application record, and answer bank for a supervised browser flow. MCP does not itself fill external forms.

An agent records jobs as it works rather than on request: `track_job` registers the listing and the user's position on it in one call, including from a non-LinkedIn careers page, and is safe to repeat as the status moves. Dashboard cards link straight to the listing they came from.

Statuses: saved, applied, pending, interview, offer, rejected. Manage applications at /dashboard or with MCP. Status updates place structures on the user's world plot.

The /world page uses React Three Fiber/three.js and refreshes itself while
visible, because Realtime is absent. Each user's land is drawn as a bordered
parcel with a post at each corner — the owner's in brand colour, everyone
else's in grey — leaving a lane of untouched ground between neighbours.
`world-scene.tsx` re-declares the plot and structure spacing that
`services/world.py` uses to place things; the two have to agree, or the
boundary would be drawn somewhere other than where the structures land.

## Ingestion

The scheduled worker finds the latest HN monthly "Who is hiring?" thread via Algolia's public API, parses top-level comments, and upserts jobs with the service role. INTERVAL_SECONDS sets the interval; the documented default is daily. Failures are logged before the next interval.

LinkedIn and Twitter/X remain human-supervised browser workflows. linkedin_ingest.py only normalizes already captured data; it does not fetch pages or hold a browser session. POST /jobs supports listing import.

Parsing limits: LinkedIn salaries come from listing headers, hourly pay is omitted, and relative posting dates are approximate. HN free-form parsing is best-effort and misses some salary formats.

Sources: [worker README](../worker/README.md), [worker loop](../worker/athena_worker/main.py), [application routes](../backend/app/api/routes/applications.py).
