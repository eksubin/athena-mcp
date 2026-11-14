# athena-mcp

An MCP server that lets an AI assistant run your job search out of
Athena.

Athena is an invite-only job-hunt platform: it ingests postings, scores
them against your resume, keeps one record per job as it moves from saved
to applied to interview, and remembers the answers you've given to the
same application questions over and over. This server is the part your
assistant talks to. Ten tools, each a typed call to the Athena API — the
ranking and the profile extraction happen server-side, so there is no
model, no key and no data of yours on this side of the wire.

It records your job search. It never applies for a job. Submitting an
employer's form is something you do, in a browser, with your own hands —
see [Review-only, and why](#review-only-and-why).

## What you need first

1. **An invite.** Athena has no open registration; a database trigger
   refuses any address that isn't on the allowlist. Someone already
   inside has to invite you, and they'll send you the link themselves —
   Athena never emails anyone.
2. **The address of the instance** you were invited to, e.g.
   `https://api.athena.example.com`. Whoever invited you knows it.
3. **A personal access token.** Sign in to the web app, open
   **Settings**, create a token, and copy it — it's shown once and can
   only be replaced, never read back. It looks like `athena_pat_…`.

Treat the token the way you'd treat a password: it can read your resume,
your answers and your whole application history. Keep it out of prompts
and out of anything you commit.

## Connecting your assistant

One block of config, and nothing to check out or install — `uvx` fetches
and runs the server on demand. You need [uv](https://docs.astral.sh/uv/)
on your machine; everything else it handles.

```json
{
  "mcpServers": {
    "athena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/eksubin/Athena", "athena-mcp"],
      "env": {
        "ATHENA_API_URL": "https://api.athena.example.com",
        "ATHENA_TOKEN": "athena_pat_..."
      }
    }
  }
}
```

That goes wherever your client keeps MCP servers — Claude Code's or
Claude Desktop's config file, Codex's `~/.codex/config.toml`, VS Code's
`mcp.json`. Restart the client (or reload its MCP connections) and the
ten tools appear. For Codex, the equivalent is:

```sh
codex mcp add athena --env ATHENA_API_URL=https://api.athena.example.com --env ATHENA_TOKEN=athena_pat_... -- uvx --from git+https://github.com/eksubin/Athena athena-mcp
```

To pick up a new version later, add `--refresh` to the `uvx` arguments
once, or run `uvx --refresh --from git+https://github.com/eksubin/Athena athena-mcp`
by hand and restart your client.

Both settings can also come from the environment, or from a `.env` file
if you've cloned this repository (see [Working on it](#working-on-it)).
Environment variables win over the file.

### When it doesn't start

The server checks two things before offering any tool, and says what's
wrong in plain English rather than leaving you to guess:

- **"ATHENA_TOKEN is not set"** — the token never reached the process.
  Check it's inside the `env` block above and not somewhere your client
  ignores.
- **"rejected this token"** — the token was revoked, belongs to a
  different instance, or your access was withdrawn. Make a new one under
  Settings.
- **"speaks API contract N, but the server…"** — your copy is older than
  the instance supports. Update it with `--refresh` as above.
- **"cannot reach …"** — it starts anyway and each tool reports the real
  error; usually a wrong `ATHENA_API_URL` or an instance that's down.

If `uvx` itself fails with a certificate error, you're behind a TLS-
inspecting proxy or antivirus: add `--system-certs` to the `uvx`
arguments, before `--from`.

## The ten tools

**Finding and reading jobs**

| Tool | What it does |
| --- | --- |
| `search_jobs` | The ranked shortlist Athena has already scored against your resume — id, title, company, score, link, location, salary, easy-apply. No descriptions; they'd swamp the context. |
| `get_job` | Everything about one listing, descriptions included. For when the shortlist isn't enough. |

**Keeping the record straight**

| Tool | What it does |
| --- | --- |
| `track_job` | The one that matters. One call records a listing *and* where you stand on it, for any job URL, with no prior lookup. Called again for the same link it updates that record instead of adding a second — so it's safe to call constantly, and it's meant to be. |
| `import_linkedin_job` | The same thing behind a stricter check that the URL really is a LinkedIn listing and not a search page. |
| `save_job` | Marks a job you're considering, by Athena id. |
| `update_status` | Moves an application: saved, applied, pending, interview, offer, rejected. |
| `get_queue` | Your applications, optionally by status, each carrying its listing — so an assistant can tell you where everything stands in one call. |

**Applying**

| Tool | What it does |
| --- | --- |
| `start_application` | Gathers what the form will ask for: the job, your profile facts, your whole answer bank, and the application record. Preparation only — it returns `"submitted": false` because it cannot submit anything. |
| `record_answer` | Saves an answer you've just given so you never type it again. Mark salary, visa status and the like `sensitive=true` and you'll be asked before it's ever reused. |
| `get_profile` | Your structured profile facts, each with a confidence — not the raw resume text. |

The server tells your assistant, in its own instructions, to call
`track_job` for every listing it handles the moment it handles it, with
whatever status is actually true, without being asked and without asking
permission. Recording a job is bookkeeping, not an action taken on your
behalf, and a job search that you have to remember to log is a job search
with holes in it.

## The skill

`skills/athena-jobs/` is a skill for Claude that goes with this server. It
makes job-hunt work conditional on Athena: its first step calls
`get_profile`, and if the tools are missing or the call fails it stops and
says how to connect instead of searching or applying unrecorded. Once
connected, it records every listing it handles with `track_job`, saves new
form answers with `record_answer`, and only marks a job `applied` after the
employer's confirmation.

Copy the folder into your skills directory and restart Claude:

```sh
# macOS / Linux
cp -r skills/athena-jobs ~/.claude/skills/
```

```powershell
# Windows
Copy-Item -Recurse skills\athena-jobs $HOME\.claude\skills\
```

A skill is instructions, not a lock: it stops a cooperative assistant from
working without Athena, and nothing more.

## Review-only, and why

Athena stores job-search data. It does not submit employer applications,
and none of the ten tools can:

- `start_application` prepares context and returns `"submitted": false`.
- `track_job` and `update_status` record a status. Recording `applied`
  applies to nothing — it's a note about something that already happened.
- Nothing here opens a browser, fills a form, presses a button or
  messages a recruiter.

So the guardrails are about honesty of the record, not about preventing
the tools from doing something they can't do:

- An application stays **saved** until a human has authorized a
  submission and seen the employer's own confirmation. A successful
  Athena API response is not evidence that anything was submitted.
- When you ask for a review-only run, the application stays saved. Your
  assistant must not mark it applied because the form looked finished.
- Answers come from verified profile facts. Missing facts, low-confidence
  facts and anything marked sensitive get asked about, not guessed —
  never an invented qualification, and never a sign-in challenge worked
  around.

Those are instructions the server gives your assistant, not a lock on
what your assistant can do elsewhere. A browser tool in the same session
can still press Submit. If that matters to you, say so in your prompt and
check the result.

### A review-only run, end to end

> Use Athena and my browser to prepare one job from my LinkedIn job
> tracker. Use my existing resume and verified facts. Stop at the review
> screen; do not submit or mark the job Applied.

1. Open the listing in a browser and read it.
2. `track_job` with what's on the page — URL, title, company, location,
   salary, whatever else is there — status left at `saved`. You get back
   the Athena job id and the application record.
3. `start_application(job_id)` for the profile facts and answer bank, so
   the form-filling step doesn't ask you what Athena already knows.
4. Follow the application link. Fill in what the verified facts cover;
   ask about the rest.
5. Stop at review. Show the screen and the outstanding questions. Leave
   the application **saved**.
6. Only after an authorized submission and a visible confirmation from
   the employer: `update_status(job_id, "applied", note)`, or `track_job`
   with `status="applied"`, carrying that evidence.

## Working on it

```sh
git clone https://github.com/eksubin/Athena
cd Athena
cp .env.example .env     # ATHENA_API_URL and your token
uv sync
uv run athena-mcp        # or point your client's "command" at uv --directory
```

With a checkout, `.env` at the repository root is read as a fallback for
both settings; it's gitignored.

```sh
uv run python -m unittest discover -s tests -v
```

Unit tests, no network: URL validation, the fields `track_job` does and
doesn't send, the idempotent save, and both directions of the version
handshake.

```sh
uv run python scripts/smoke_test.py
```

The integration check, and the only thing that exercises this client and
a real Athena deployment together. It creates a disposable account, runs
all ten tools over stdio against it, and deletes the account, its invite
and its jobs afterwards. It needs the instance's own secrets, so it's an
operator's tool:

| Variable | |
| --- | --- |
| `ATHENA_API_URL` | default `http://localhost:8000` |
| `ATHENA_SUPABASE_URL` | default `http://localhost:8001` |
| `SUPABASE_SERVICE_ROLE_KEY` | required |
| `SUPABASE_JWT_SECRET` | required |

It never contacts an employer.

## The other side

The backend, web app, ingestion worker and database live in the
Athena platform's own repository, which is private. Because the two
ship separately and users update this one on their own schedule, the API
surface between them is versioned and checked at startup:
[CONTRACT.md](CONTRACT.md) is what it covers and what moves the number.
