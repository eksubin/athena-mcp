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

- **Claude** — Claude in Chrome, because LinkedIn and most employer sites
  need the user's own login. Use the built-in browser pane only when
  Claude in Chrome is not available, and expect to ask the user to sign
  in to LinkedIn there.
- **ChatGPT / Codex** — its own built-in browser or agent browsing tool.

Do not look for or start a third-party browser agent such as BrowserOS.
If the assistant has no browser tool in this session, say so: listings the
user pastes can still be recorded and tracked, but forms cannot be filled.

When a site asks the user to sign in, stop and let them do it in that
browser; never type their password.

## 3. Set up before searching: CV and cover letter

Do this early, before any search.

The user keeps their CV and a basic cover letter in one folder on their
computer, and this skill reads the latest files from it on every run.

1. Look for the folder. The default is `Documents/Athena` in the user's
   home folder; if they have told you a different one, use that.
2. If the folder is missing or empty, ask the user - in one message - to
   create it and put two files in it, then wait:
   - their CV (PDF, DOCX or TXT), and
   - a basic cover letter to adapt for each role.
   Tell them they can replace these files whenever they like, and that
   the newest CV in the folder is the one used from then on - there is
   nothing else to update.
3. Read the most recently modified CV and cover letter in the folder.
   If there are several of either, use the newest and say which file you
   picked.
4. If there is a CV but no cover letter, offer to draft one from the CV,
   show it, and save it into the folder only once the user approves it.
5. If this session has no access to the user's files, ask them to attach
   or paste the CV and cover letter instead, and say why.

Then:

- Work from the CV in the folder together with the facts `get_profile`
  returned. Where the two disagree, the newer CV wins; mention the
  difference and suggest uploading that CV under **My profile** in
  Athena so the website matches. This skill cannot upload it for them.
- Ask about facts that are missing or low-confidence; never guess a
  qualification.
- Call `get_queue` so jobs already saved or applied to are recognised
  rather than treated as new.

If the user says to go ahead without a CV or cover letter, continue and
note what is missing.

## 4. Where to search: LinkedIn first

LinkedIn Jobs is the primary place to search. Go straight to
`https://www.linkedin.com/jobs/` in the browser from section 2.

1. Open LinkedIn and check the user is signed in. If it shows a sign-in
   or join page, stop and ask the user to log in to LinkedIn in that
   browser, then tell you when they are in. Do not type their
   credentials and do not continue signed out.
2. Search LinkedIn Jobs with the user's target roles, location and remote
   preference from the profile, and use LinkedIn's own filters (date
   posted, experience level, remote, Easy Apply) to narrow the results.
3. Open each promising listing and read it on LinkedIn before recording
   it.

Do not start from Google, another search engine, or a general web
search, and do not wander to unrelated sites. Other sources are allowed
only in these cases:

- `search_jobs` - roles Athena has already ranked for the user; fine to
  use alongside LinkedIn.
- The employer's own careers page, when a LinkedIn listing sends the
  application there.
- A site or link the user names themselves.

If LinkedIn cannot be reached or the user will not sign in, say so and
ask where they want to search instead of picking another site yourself.

## 5. Record every job, as it happens

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

## 6. Applying

1. `track_job` the listing as `saved` and keep the Athena job id it returns.
2. `start_application(job_id)` for the profile facts and the answer bank
   before touching the form, so questions Athena already holds are not
   asked again. Where the form takes a cover letter, adapt the one from the
   folder (section 3) to this role and show it to the user first. Upload
   the CV file from that folder when the form asks for a resume.
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

## 7. Close the run

Call `get_queue` and report from it, not from memory: what was added,
what changed status, and anything that could not be recorded.
