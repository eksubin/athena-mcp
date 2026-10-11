"""Normalises LinkedIn saved-job captures into `jobs` rows.

Deliberately *not* a scraper. Unlike `hn_ingest`, nothing in this module
fetches anything: it takes captures that a supervised browser already
collected and turns them into rows. See README.md ("Why LinkedIn and
Twitter/X aren't here") — an unattended worker logging into LinkedIn on a
schedule can get the user's own account flagged, and that call isn't this
worker's to make. So the fetch stays human-supervised and the parsing,
which is the part worth testing and reusing, lives here.

A capture is whatever the browser agent read off the page:

    {
        "external_id": "4466870501",       # the /jobs/view/<id>/ id
        "title": "Gen AI Architect",
        "company_line": "HMG AMERICA LLC · United States (Remote)",
        "posted": "Posted 6d ago",         # or "6 days ago"
        "apply_label": "Easy Apply",       # or "Apply"
        "salary_raw": "$347K/yr - $385K/yr",
        "workplace": "Remote",
        "description": "About the job ...",
    }

Only `external_id` and enough to derive a title/company are required;
everything else degrades to None rather than raising, because a saved-jobs
list is a lossy view of a listing and half these fields are simply absent.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any

SOURCE = "linkedin"
JOB_URL = "https://www.linkedin.com/jobs/view/{id}/"

# LinkedIn writes the company and place on one line, middot-separated, with
# the workplace type parenthesised: "Nscale · New York, NY (Hybrid)".
_COMPANY_SEP = "·"
_WORKPLACE_RE = re.compile(r"\s*\(([^)]+)\)\s*$")

# "$347K/yr - $385K/yr", "$150,000/yr", "$60/hr". Hourly rates are captured
# but not converted — an hourly figure isn't comparable to the yearly floor
# in a user's preferences, and inventing an annualisation would be a guess.
_MONEY_RE = re.compile(r"\$\s*([\d][\d.,]*)\s*([KkMm]?)")
_HOURLY_RE = re.compile(r"/\s*hr\b", re.IGNORECASE)

# "6d ago", "6 days ago", "Reposted 1 week ago", "3 weeks ago", "2mo ago".
_RELATIVE_RE = re.compile(
    r"(\d+)\s*(mo|m|d|w|y|minute|hour|day|week|month|year)s?\s+ago", re.IGNORECASE
)
_UNIT_DAYS = {
    "minute": 0, "hour": 0,
    "d": 1, "day": 1,
    "w": 7, "week": 7,
    "mo": 30, "month": 30,
    "m": 30,
    "y": 365, "year": 365,
}

_REMOTE_WORKPLACES = {"remote"}


def split_company_line(line: str) -> tuple[str, str | None, str | None]:
    """"Nscale · New York, NY (Hybrid)" -> ("Nscale", "New York, NY", "Hybrid")."""
    if not line:
        return "", None, None

    company, _, rest = line.partition(_COMPANY_SEP)
    company = company.strip()
    rest = rest.strip()
    if not rest:
        return company, None, None

    workplace = None
    match = _WORKPLACE_RE.search(rest)
    if match:
        workplace = match.group(1).strip()
        rest = rest[: match.start()].strip()

    return company, rest or None, workplace


def parse_salary(raw: str | None) -> tuple[int | None, int | None]:
    """Returns (min, max) in whole currency units, or (None, None).

    Callers must pass a value scraped from the listing *header*. The page
    also renders salaries for unrelated "similar jobs" further down, and
    matching those against the wrong listing is worse than storing nothing.
    """
    if not raw or _HOURLY_RE.search(raw):
        return None, None

    values = []
    for amount, suffix in _MONEY_RE.findall(raw):
        try:
            value = float(amount.replace(",", ""))
        except ValueError:
            continue
        if suffix.upper() == "K":
            value *= 1_000
        elif suffix.upper() == "M":
            value *= 1_000_000
        values.append(int(round(value)))

    if not values:
        return None, None
    return min(values), max(values)


def parse_relative_date(text: str | None, now: datetime | None = None) -> str | None:
    """"Reposted 1 week ago" -> an ISO timestamp, to day resolution.

    LinkedIn never exposes an absolute posting date on these pages, so this
    is approximate by construction — good to the day at best.
    """
    if not text:
        return None

    match = _RELATIVE_RE.search(text)
    if not match:
        return None

    count = int(match.group(1))
    unit = match.group(2).lower()
    if unit not in _UNIT_DAYS:
        return None

    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=_UNIT_DAYS[unit] * count)).isoformat()


def to_job_row(capture: dict[str, Any], now: datetime | None = None) -> dict[str, Any] | None:
    """One capture -> one `jobs` row, or None if it can't be identified."""
    external_id = str(capture.get("external_id") or "").strip()
    if not external_id:
        return None

    company = (capture.get("company") or "").strip()
    location = capture.get("location")
    workplace = capture.get("workplace")

    if capture.get("company_line"):
        parsed_company, parsed_location, parsed_workplace = split_company_line(
            capture["company_line"]
        )
        company = company or parsed_company
        location = location or parsed_location
        workplace = workplace or parsed_workplace

    title = (capture.get("title") or "").strip()
    if not title or not company:
        return None

    salary_min, salary_max = parse_salary(capture.get("salary_raw"))

    return {
        "source": SOURCE,
        "external_id": external_id,
        "title": title[:200],
        "company": company[:200],
        "url": capture.get("url") or JOB_URL.format(id=external_id),
        "description": (capture.get("description") or "").strip() or None,
        "location": location[:200] if location else None,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "remote": (workplace or "").strip().lower() in _REMOTE_WORKPLACES,
        "easy_apply": (capture.get("apply_label") or "").strip().lower() == "easy apply",
        "posted_at": parse_relative_date(capture.get("posted"), now),
    }


def to_job_rows(
    captures: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """Captures -> rows, dropping unidentifiable ones and de-duplicating.

    The saved-jobs list paginates, and re-reading a page mid-scroll can hand
    back the same listing twice; upserting a batch that repeats a key fails
    outright, so the de-dupe happens here rather than at the database.
    """
    rows: dict[str, dict[str, Any]] = {}
    for capture in captures:
        row = to_job_row(capture, now)
        if row:
            rows[row["external_id"]] = row
    return list(rows.values())


def run(captures: list[dict[str, Any]], supabase_client) -> int:
    """Upserts captured listings. Returns the number of rows written.

    Takes already-collected captures, not a session — see the module
    docstring. The upsert key matches the worker's own ingest, so re-running
    over the same saved list updates rows instead of duplicating them.
    """
    rows = to_job_rows(captures)
    if not rows:
        return 0
    supabase_client.table("jobs").upsert(rows, on_conflict="source,external_id").execute()
    return len(rows)
