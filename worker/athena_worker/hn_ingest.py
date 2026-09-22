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
    `Company | Role | Location | Remote/Onsite | ...`. Not every poster
    follows it exactly, so this is best-effort, not a strict parser."""
    raw = comment.get("text")
    if not raw:
        return None

    plain = _strip_html(raw)
    first_line, _, rest = plain.partition("\n")
    parts = [p.strip() for p in first_line.split("|") if p.strip()]
    if not parts:
        return None

    company = parts[0]
    title = parts[1] if len(parts) > 1 else first_line
    location = parts[2] if len(parts) > 2 else None

    salary_matches = [int(m.group(1)) * 1000 for m in _SALARY_RE.finditer(first_line)]
    salary_min = min(salary_matches) if salary_matches else None
    salary_max = max(salary_matches) if salary_matches else None

    href_match = _HREF_RE.search(raw)
    apply_url = (
        html.unescape(href_match.group(1))
        if href_match
        else f"https://news.ycombinator.com/item?id={comment['id']}"
    )

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
