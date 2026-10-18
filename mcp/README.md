# Athena with Codex and BrowserOS

Athena's MCP provides job data, profile facts, reusable answers, and tracking.
BrowserOS operates LinkedIn and employer application forms. Calling
`track_job`, `start_application` or `update_status` does not submit an employer
application.

Athena expects to be kept current without being asked. Call `track_job` for
every listing you handle, as soon as you handle it, with the status that is
true at that moment — it registers the listing and the application record in
one call, works for any job URL rather than LinkedIn alone, and updates the
existing record when called again for the same link. Pass everything you read
off the page: link, title, company, location, salary range, remote and
easy-apply flags, posting date, description. Recording is bookkeeping; `applied`
still requires an authorized submission and visible employer confirmation.

## Connect Codex on this Windows checkout

1. Start the Docker stack with `docker compose up -d` at the repository root.
2. Sign into Athena, open Settings, and create a token named **Codex desktop**.
3. Store it in `mcp/.env` using `mcp/.env.example` as the template. This file is
   gitignored. Never put the token into prompts or committed configuration.
4. Install the MCP dependencies with `uv sync` in `mcp/`.
5. From PowerShell, register the server:

```powershell
codex mcp add athena -- C:/Users/BridgeAiHub/Documents/Projects/Athena/mcp/.venv/Scripts/python.exe -m athena_mcp.server
codex mcp get athena
```

The path above is specific to this checkout. Use your absolute Python path
elsewhere. The server resolves `mcp/.env` independently of its launch directory.
Environment variables override that file. Restart Codex's MCP connections or
restart the app to expose newly added tools in the chat. BrowserOS must also be
connected and signed into the intended LinkedIn account.

Codex supports local stdio MCP servers and reads their initialization
instructions: [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Review-only walkthrough

Example prompt:

> Use Athena and BrowserOS to prepare one job from my LinkedIn Job tracker.
> Use my existing resume and verified facts. Stop at the review screen;
> do not submit or mark the job Applied.

1. Read LinkedIn's Job tracker in BrowserOS and select an eligible saved job.
2. Read the actual listing, then call `track_job` with its observed URL, title,
   company, location and whatever else the page shows — leaving the status at
   `saved`. It returns the Athena job ID and the application record. (
   `import_linkedin_job` does the same behind a stricter LinkedIn URL check.)
3. Call `start_application(job_id)`. Inspect the application status, job,
   profile facts with confidence, and answer bank. Existing statuses are retained.
4. Follow the job's application link in BrowserOS. Some jobs use Easy Apply;
   others redirect to an employer portal. Read every required field.
5. Use the chosen resume and verified information. Ask for missing information,
   low-confidence facts, and sensitive answers; never infer eligibility answers.
6. Stop at review and show a screenshot and outstanding questions. Leave new
   applications **Saved**. Do not press Submit, Send, or a combined final-action
   button during a review-only run. A consent gate may require user approval.
7. Only for an explicitly authorized submission: inspect the employer's success
   screen, then call `update_status(job_id, "applied", note)` — or `track_job`
   with `status="applied"` — carrying the confirmation evidence. A successful
   Athena API response alone is not submission evidence.

The server instructions guide this workflow; they are not a technical lock on
browser actions or status changes. An agent must still respect the user's scope.

## Verification

From the repository root:

```powershell
mcp/.venv/Scripts/python.exe -m unittest discover -s mcp/tests -v
mcp/.venv/Scripts/python.exe scripts/mcp_smoke_test.py
```

The smoke check exercises all ten tools with a disposable account. It checks
startup from a different directory, discovery, typed status schemas, profile
facts, preparation without submission, saving without resetting status,
one-call tracking with a status, and that every record it reads back carries
the listing's link. Registration is closed, so it allowlists its disposable
address first; its invite, account and jobs are deleted afterward. It never
contacts an employer.

For a real browser verification, confirm the selected job is visible in Athena,
the employer form is populated correctly, and the final submission button has
not been clicked. Missing files or mandatory answers must be reported as blocked,
not counted as a completed application.
