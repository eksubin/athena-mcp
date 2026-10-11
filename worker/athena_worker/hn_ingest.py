"""Ingests HN's monthly "Who is hiring?" thread into the `jobs` table.

Uses the Algolia HN Search API (public, unauthenticated, meant for exactly
this kind of use) — not the site itself, so there's nothing to scrape and
no rate-limit/ToS concern the way there would be automating a login-gated
platform. See worker/README.md for why LinkedIn/Twitter aren't handled
this way.
"""

import html
import re
from datetime import datetime, timezone
from typing import Any

import httpx

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ALGOLIA_ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"

_TAG_RE = re.compile(r"<[^>]+>")
_SALARY_RE = re.compile(r"[$£€]\s?(\d{2,3})\s?[kK]\b")
_HREF_RE = re.compile(r'href="([^"]+)"')
_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)

# Posters don't agree on field order, so each pipe-separated part is
# classified by what it looks like rather than by position. The role check
# runs before the location check on purpose: "Remote Frontend Engineer"
# carries both signals, and it is a title.
_URL_PART_RE = re.compile(
    r"^(?:https?://|www\.)|^[\w.-]+\.(?:com|io|ai|dev|co|org|net|xyz|so|app|tech)(?:/|$)",
    re.IGNORECASE,
)
_WORKPLACE_RE = re.compile(r"\b(?:remote|onsite|on-site|hybrid|wfh)\b", re.IGNORECASE)
_ROLE_RE = re.compile(
    r"\b(?:engineer|engineering|developer|programmer|scientist|designer|manager|"
    r"architect|analyst|researcher|swe|sre|devops|mlops|intern|internship|founding|"
    r"full[- ]?stack|fullstack|frontend|front-end|backend|back-end|lead|head|"
    r"director|cto|staff|principal|senior|junior|consultant|specialist)\b",
    re.IGNORECASE,
)
_CITY_STATE_RE = re.compile(r"^[A-Z][\w .'-]+,\s*(?:[A-Z]{2}\b|[A-Z][a-z]+)")
_EMPLOYMENT_RE = re.compile(
    r"^\(?(?:full[- ]?time|part[- ]?time|contract|contractor|freelance|permanent|"
    r"intern(?:ship)?|temporary|c2c|w2)\)?$",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(r"^[^\w]*[$£€]")
_PLACE_WORDS = frozenset(
    {
        "sf", "sfo", "nyc", "uk", "us", "usa", "eu", "emea", "apac", "bay area",
        "san francisco", "new york", "london", "berlin", "paris", "amsterdam",
        "toronto", "vancouver", "sydney", "melbourne", "singapore", "tokyo",
        "bangalore", "austin", "seattle", "boston", "chicago", "denver",
        "worldwide", "anywhere", "global", "europe", "north america", "canada",
        "germany", "india", "australia", "united states",
    }
)


def _is_location(part: str) -> bool:
    """Location-ish. Only consulted after the role check has already failed."""
    if _CITY_STATE_RE.match(part):
        return True
    stripped = part.lower().strip("()[] ")
    if stripped in _PLACE_WORDS or _WORKPLACE_RE.search(part):
        return True
    return any(word in stripped for word in _PLACE_WORDS)


def _split_fields(parts: list[str]) -> tuple[str | None, str | None, str | None]:
    """Returns (title, location, url) from the parts following the company.

    Anything nothing matched falls back to the old positional guess, so a
    well-formed `Company | Role | Location` post parses exactly as before,
    while `Company | https://x.com | Role | Remote` no longer lands the URL
    in the title and the role in the location.
    """
    title = location = url = None
    leftovers: list[str] = []

    for part in parts:
        if url is None and _URL_PART_RE.match(part):
            url = part
        elif _EMPLOYMENT_RE.match(part) or _MONEY_RE.match(part):
            continue
        elif title is None and _ROLE_RE.search(part):
            title = part
        elif location is None and _is_location(part):
            location = part
        else:
            leftovers.append(part)

    if title is None and leftovers:
        title = leftovers.pop(0)
    if location is None and leftovers:
        location = leftovers.pop(0)
    return title, location, url


def _strip_html(text: str) -> str:
    text = text.replace("<p>", "\n\n")
    text = _TAG_RE.sub("", text)
    return html.unescape(text).strip()


def find_latest_thread_id(client: httpx.Client) -> int:
    resp = client.get(
        ALGOLIA_SEARCH_URL,
        params={"tags": "story,author_whoishiring", "hitsPerPage": 1},
    )
    resp.raise_for_status()
    hits = resp.json()["hits"]
    if not hits:
        raise RuntimeError("no 'Who is hiring' thread found")
    return int(hits[0]["objectID"])


def fetch_thread(client: httpx.Client, thread_id: int) -> dict[str, Any]:
    resp = client.get(ALGOLIA_ITEM_URL.format(id=thread_id))
    resp.raise_for_status()
    return resp.json()


def parse_comment(comment: dict[str, Any]) -> dict[str, Any] | None:
    """HN's own convention for this thread is a pipe-separated first line:
    `Company | Role | Location | Remote/Onsite | ...`. Plenty of posters
    reorder it or slot a URL in second, so only the company is read
    positionally; the rest is classified by shape in `_split_fields`."""
    raw = comment.get("text")
    if not raw:
        return None

    plain = _strip_html(raw)
    first_line, _, rest = plain.partition("\n")
    parts = [p.strip() for p in first_line.split("|") if p.strip()]
    if not parts:
        return None

    company = parts[0]
    title, location, url_part = _split_fields(parts[1:])
    if title is None:
        title = first_line

    salary_matches = [int(m.group(1)) * 1000 for m in _SALARY_RE.finditer(first_line)]
    salary_min = min(salary_matches) if salary_matches else None
    salary_max = max(salary_matches) if salary_matches else None

    href_match = _HREF_RE.search(raw)
    if href_match:
        apply_url = html.unescape(href_match.group(1))
    elif url_part:
        apply_url = url_part if url_part.startswith("http") else f"https://{url_part}"
    else:
        apply_url = f"https://news.ycombinator.com/item?id={comment['id']}"

    posted_at = None
    if comment.get("created_at_i"):
        posted_at = datetime.fromtimestamp(comment["created_at_i"], tz=timezone.utc).isoformat()

    return {
        "source": "hn",
        "external_id": str(comment["id"]),
        "title": title[:200],
        "company": company[:200],
        "url": apply_url,
        "description": rest.strip() or first_line,
        "location": location[:200] if location else None,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "remote": bool(_REMOTE_RE.search(first_line)),
        "easy_apply": False,
        "posted_at": posted_at,
    }


def parse_thread(thread: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for comment in thread.get("children", []):
        if comment.get("type") != "comment":
            continue
        if comment.get("deleted") or comment.get("dead"):
            continue
        parsed = parse_comment(comment)
        if parsed:
            rows.append(parsed)
    return rows


def run(client: httpx.Client, supabase_client) -> int:
    """Returns the number of job rows upserted."""
    thread_id = find_latest_thread_id(client)
    thread = fetch_thread(client, thread_id)
    rows = parse_thread(thread)
    if not rows:
        return 0
    supabase_client.table("jobs").upsert(rows, on_conflict="source,external_id").execute()
    return len(rows)
