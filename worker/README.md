# Athena ingestion worker — Phase 3

Automates exactly one source: Hacker News's monthly ["Who is hiring?"
thread](https://news.ycombinator.com/submitted?id=whoishiring), via the
public [Algolia HN Search API](https://hn.algolia.com/api) — no login, no
scraping, no ToS to violate. Runs on a loop (`INTERVAL_SECONDS`, default
daily), finds the latest thread, best-effort parses each top-level comment's
`Company | Role | Location | Remote/Onsite | ...` convention, and upserts
into `jobs` using the service role (the only writer the table's RLS policy
allows — see `supabase/migrations/0001_init.sql`).

## Why LinkedIn and Twitter/X aren't here

The original `job-apply-plugin` searches those two with a **visible,
human-supervised browser** — the user's own authenticated session does the
searching, at human pace, with a person watching. An unattended worker
scraping LinkedIn on a schedule is a materially different risk: it can get
the user's own account flagged or banned for automated activity in a way
the supervised-browser approach doesn't. That tradeoff isn't this worker's
to make unilaterally, so LinkedIn/Twitter search stays exactly as it is
today — a skill-driven, visible-browser flow — and isn't automated here.

## Parsing is best-effort, not a guarantee

HN's `Company | Role | Location | ...` convention isn't enforced, so
`athena_worker/hn_ingest.py` degrades gracefully rather than failing: a post
that doesn't follow the convention still gets a row (with less-useful
`title`/`company` values) instead of being dropped. Salary extraction in
particular only catches amounts written with a currency symbol directly
before each number (`$150k-$190k`, not `$150k-190k`) — a real, known gap,
not a bug to chase down without cause.

## Running it

```sh
cp .env.example .env
uv sync
uv run pytest              # parser tests, run against real captured HN text
uv run python -m athena_worker.main
```
