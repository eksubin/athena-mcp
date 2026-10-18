"""Turning an arbitrary job URL into a stable catalog identity.

`jobs` is keyed on (source, external_id) so that re-seeing the same
listing updates one row instead of accumulating near-duplicates. The
worker gets those two values for free — it reads a feed. An agent working
in a browser does not: it has a URL off the address bar, usually carrying
tracking parameters that differ on every visit. Deriving the key here,
rather than in the MCP client, means every caller that tracks a listing
agrees on what counts as "the same job".
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from app.core.supabase import service_client

# Parameters that identify how someone arrived at a listing, not which
# listing it is. Left in, the same job saved from a search page and from an
# email would become two rows.
_TRACKING_PARAMS = {
    "ref",
    "refid",
    "trk",
    "trackingid",
    "traceid",
    "origin",
    "position",
    "pagenum",
    "eboriginal",
    "savedsearchid",
    "alternatechannel",
    "src",
    "source",
    "gh_src",
    "lever-source",
    "lever-origin",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
}

_LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com", "uk.linkedin.com", "in.linkedin.com"}


class UnusableJobUrl(ValueError):
    """The URL can't be used as a listing identity (not an absolute web URL)."""


def _canonical_url(parts) -> str:
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS
    )
    path = parts.path.rstrip("/") or "/"
    host = (parts.hostname or "").lower().removeprefix("www.")
    return f"{host}{path}" + (f"?{urlencode(query)}" if query else "")


def identify_listing(url: str) -> tuple[str, str]:
    """Return the (source, external_id) catalog key for a job URL.

    Known job boards get their own identifier, so the same listing is one
    row regardless of which URL shape it was seen through. Anything else
    falls back to the site's hostname plus a digest of the cleaned URL —
    stable across revisits, without pretending to understand the site.
    """
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise UnusableJobUrl("A job link must be a full http(s) URL")

    host = parts.hostname.lower()
    path = parts.path
    query = dict(parse_qsl(parts.query))

    if host in _LINKEDIN_HOSTS:
        # Both the listing page and the search page's selected job; the
        # latter is what an agent reading a results page actually has.
        match = re.search(r"/jobs/view/(\d+)", path)
        job_id = match.group(1) if match else query.get("currentJobId")
        if job_id and job_id.isdigit():
            return "linkedin", job_id

    if host.endswith("greenhouse.io"):
        match = re.search(r"/([^/]+)/jobs/(\d+)", path)
        if match:
            return "greenhouse", f"{match.group(1)}/{match.group(2)}"

    if host.endswith("lever.co"):
        match = re.search(r"/([^/]+)/([0-9a-f-]{16,})", path)
        if match:
            return "lever", f"{match.group(1)}/{match.group(2)}"

    canonical = _canonical_url(parts)
    source = host.removeprefix("www.")
    return source, hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def upsert_jobs(rows: list[dict]) -> list[dict]:
    """Write listings to the shared catalog.

    Goes through the service client, not a user-scoped one: `jobs` belongs
    to everyone, and its RLS grants `authenticated` select only — a
    user-scoped write would be refused by policy. Callers are still
    authenticated; the row they write just isn't theirs.

    Rows should come from `model_dump(exclude_unset=True)` so an import
    that only observed a title and URL does not blank out a description or
    salary another source already collected for the same listing.
    """
    if not rows:
        return []
    return (
        service_client().table("jobs").upsert(rows, on_conflict="source,external_id").execute()
    ).data
