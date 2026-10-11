"""Ranks jobs against one user's stated preferences.

`search_jobs` calls this for every candidate row and returns only the top
handful, so this function decides what an agent ever gets to see. The shape
is: three additive components worth 100 between them, then two multipliers
that can only pull a score down (recency decay, per-source weighting).

Keeping the multipliers separate from the components matters — a perfect
match with an unknown posting date still scores 100, rather than being
quietly penalised for a field the ingester happened not to fill in.
"""

from datetime import datetime, timezone

# Component ceilings. They sum to 100 on purpose.
_TITLE_WEIGHT = 45
_SALARY_WEIGHT = 30
_REMOTE_WEIGHT = 25

# Recency: full credit up to _FRESH_DAYS, then a straight line down to
# _STALE_FACTOR at _STALE_DAYS. Old postings are demoted, never eliminated —
# a six-month-old listing that matches perfectly still beats a fresh one
# that matches nothing.
_FRESH_DAYS = 14
_STALE_DAYS = 90
_STALE_FACTOR = 0.6

# Tokens that carry no matching signal in a job title.
_STOPWORDS = frozenset({"a", "an", "and", "of", "the", "for", "to", "in", "at", "-", "/"})


def _tokens(text: str) -> set[str]:
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
    return {t for t in cleaned.split() if t and t not in _STOPWORDS}


def _title_score(job_title: str, wanted: list[str]) -> tuple[int, float]:
    """Best token-overlap across the user's wanted titles, scaled to weight.

    Substring matching was too brittle: "imaging scientist" missed "Senior
    Scientist, Imaging" purely on word order. Overlap is order-free, so a
    preference is matched when all of its words appear, however arranged.
    """
    if not wanted:
        return 0, 0.0

    job_tokens = _tokens(job_title)
    if not job_tokens:
        return 0, 0.0

    best = 0.0
    for want in wanted:
        want_tokens = _tokens(want)
        if not want_tokens:
            continue
        best = max(best, len(want_tokens & job_tokens) / len(want_tokens))

    return round(_TITLE_WEIGHT * best), best


def _salary_score(job: dict, floor: int | None) -> tuple[int, str]:
    """Partial credit when the salary is unknown.

    Most listings simply don't publish a range, and scoring those as a hard
    zero buried every one of them below any listing that did — which is a
    statement about disclosure habits, not about fit.
    """
    if floor is None:
        return _SALARY_WEIGHT, "no_floor_set"

    job_max = job.get("salary_max")
    if job_max is None:
        return _SALARY_WEIGHT // 2, "unknown"
    if job_max >= floor:
        return _SALARY_WEIGHT, "ok"
    if job_max >= floor * 0.8:
        return _SALARY_WEIGHT // 2, "near_floor"
    return 0, "below_floor"


def _remote_score(job: dict, remote_only: bool) -> tuple[int, bool]:
    is_remote = bool(job.get("remote"))
    if remote_only:
        return (_REMOTE_WEIGHT, True) if is_remote else (0, False)
    return (_REMOTE_WEIGHT if is_remote else 18), is_remote


def _recency_factor(posted_at) -> float:
    if not posted_at:
        return 1.0

    if isinstance(posted_at, str):
        try:
            posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        except ValueError:
            return 1.0
    else:
        posted = posted_at

    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)

    age_days = (datetime.now(timezone.utc) - posted).days
    if age_days <= _FRESH_DAYS:
        return 1.0
    if age_days >= _STALE_DAYS:
        return _STALE_FACTOR

    span = _STALE_DAYS - _FRESH_DAYS
    return 1.0 - (1.0 - _STALE_FACTOR) * (age_days - _FRESH_DAYS) / span


def _source_weight(job: dict, preferences: dict) -> float:
    """Lets a user trust one feed more than another, e.g. {"hn": 1.1}.

    Clamped so a stray value in preferences can't invert the ranking.
    """
    weights = preferences.get("source_weights") or {}
    try:
        weight = float(weights.get(job.get("source"), 1.0))
    except (TypeError, ValueError):
        return 1.0
    return max(0.5, min(1.5, weight))


def score_job(job: dict, preferences: dict) -> tuple[int, dict]:
    """Returns (score 0-100, signals) for one job against one user's prefs.

    `signals` is persisted alongside the score in `job_scores`, so it is
    written to be read by a human debugging a ranking that looks wrong —
    every component is reported, not just the ones that fired.
    """
    title_points, title_ratio = _title_score(job.get("title") or "", preferences.get("titles", []))
    salary_points, salary_verdict = _salary_score(job, preferences.get("salary_min"))
    remote_points, is_remote = _remote_score(job, bool(preferences.get("remote_only")))

    base = title_points + salary_points + remote_points
    recency = _recency_factor(job.get("posted_at"))
    source = _source_weight(job, preferences)
    score = max(0, min(100, round(base * recency * source)))

    signals: dict = {
        "title_points": title_points,
        "title_overlap": round(title_ratio, 2),
        "salary_points": salary_points,
        "salary": salary_verdict,
        "remote_points": remote_points,
        "recency_factor": round(recency, 2),
        "source_weight": source,
        "base": base,
    }
    # Kept from the original scorer: these three booleans are what the rest
    # of the system (and its tests) look for to mean "this actually matched".
    if title_ratio >= 1.0:
        signals["title_match"] = True
    if remote_points and is_remote:
        signals["remote_match"] = True
    if salary_verdict in ("ok", "no_floor_set"):
        signals["salary_ok"] = True

    return score, signals
