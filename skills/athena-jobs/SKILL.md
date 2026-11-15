---
name: athena-jobs
description: "Search, prepare, apply to and track jobs with every listing recorded in the user's Athena account. Use for any job-hunt work: finding or shortlisting jobs, reviewing a listing, filling an application, or updating where an application stands. Requires a working Athena MCP connection and stops without one."
---

# Athena jobs

Athena is the user's job-search record. This skill does job-hunt work only
while that record is reachable, and writes every job it touches into it.

## 1. Connection gate — do this first, every run

1. Check that the Athena MCP tools are present in this session
   (`get_profile`, `track_job`, `get_queue`, `start_application`,
   `record_answer`, `update_status`).
2. Call `get_profile`.

If the tools are missing, or `get_profile` returns an error, **stop here**.
Do not search for jobs, open listings, fill forms, or keep a local list
instead. Tell the user Athena is not connected and what fixes it:

- **No Athena tools at all** — the MCP server is not configured. They need
  an invite to an Athena instance, a personal access token from its
  Settings page, and the `athena` MCP server added to this client with
  `ATHENA_API_URL` and `ATHENA_TOKEN` (see the athena-mcp README).
- **Tools present but the call fails** — the instance is down or
  unreachable, or the token was revoked or belongs to another instance.
  They should check the instance is up and create a new token in Settings.

Offer to retry once they have fixed it. Nothing below runs until
`get_profile` succeeds.

If Athena stops answering part-way through a run, stop at that point,
say which jobs were recorded and which were not, and do not continue the
job work unrecorded.

## 2. Which browser to use

Use the browser that belongs to the assistant running this skill, and no
other:

- **Claude** — Claude in Chrome when the user wants their own signed-in
  Chrome (LinkedIn and most employer sites need their login), otherwise
  the built-in browser pane.
- **ChatGPT / Codex** — its own built-in browser or agent browsing tool.

Do not look for or start a third-party browser agent such as BrowserOS.
If the assistant has no browser tool in this session, say so: listings the
user pastes can still be recorded and tracked, but forms cannot be filled.

When a site asks the user to sign in, stop and let them do it in that
browser; never type their password.

## 3. Start from what Athena already knows

- Use the profile facts `get_profile` returned. Ask the user about facts
  that are missing or low-confidence; never guess a qualification.
- Call `get_queue` so jobs already saved or applied to are recognised
  rather than treated as new.

## 4. Record every job, as it happens

Call `track_job` in the same turn you handle a listing — do not batch
them for the end, and do not ask permission to record one.

- Pass everything actually read from the listing: `url`, `title`,
  `company`, `location`, `description`, `salary_min`, `salary_max`,
  `remote`, `easy_apply`, `posted_at`. Leave out what was not on the
  page; never invent a value.
- Use `note` for anything the user will want later: why it fits, a
  recruiter's name, the confirmation number, the reason it was skipped.
- Calling `track_job` again for the same link updates the record, so
  re-track whenever the status changes or more detail turns up.

Status must be what is true now:

| Status | When |
| --- | --- |
| `saved` | Found, shortlisted, being considered, or prepared but not submitted |
| `applied` | The user authorized the submission **and** the employer's confirmation was seen |
| `pending` | Submitted and waiting on something specific (assessment, referral, reply) |
| `interview` | An interview is scheduled or has happened |
| `offer` | An offer was made |
| `rejected` | The employer declined, or the user withdrew |

## 5. Applying

1. `track_job` the listing as `saved` and keep the Athena job id it returns.
2. `start_application(job_id)` for the profile facts and the answer bank
   before touching the form, so questions Athena already holds are not
   asked again.
3. Fill the employer's form in the assistant's own browser (section 2).
   Athena submits nothing itself.
4. For each new question the form asks, save the user's answer with
   `record_answer`. Mark salary, visa or sponsorship, disability, veteran
   status, demographics and similar as `sensitive=True`, and confirm
   sensitive answers with the user every time before reusing them.
5. Submit only when the user has said to submit this application. A
   request to review or prepare stops at the review screen and the job
   stays `saved`.
6. After submitting, look for the employer's confirmation (page, banner or
   email). Only then `track_job` or `update_status` to `applied`, with the
   confirmation detail in `note`. No confirmation seen means it stays
   `saved`, with a note saying what happened.

Never work around a sign-in challenge or CAPTCHA; hand those to the user.

## 6. Close the run

Call `get_queue` and report from it, not from memory: what was added,
what changed status, and anything that could not be recorded.
