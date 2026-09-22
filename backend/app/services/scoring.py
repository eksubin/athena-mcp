def score_job(job: dict, preferences: dict) -> tuple[int, dict]:
    """Placeholder scorer — title/remote/salary match only, 0-100.

    This is what search_jobs uses to decide which ~10 rows Claude actually
    sees. It's intentionally simple for now; real signal (recruiter/hiring
    manager presence, recency decay, per-source weighting) arrives with the
    Phase 3 ingestion worker, which is what actually knows those things.
    """
    signals: dict = {}
    score = 0

    titles = [t.lower() for t in preferences.get("titles", [])]
    title = (job.get("title") or "").lower()
    if titles and any(t in title for t in titles):
        score += 40
        signals["title_match"] = True

    if preferences.get("remote_only"):
        if job.get("remote"):
            score += 30
            signals["remote_match"] = True
    else:
        score += 15

    salary_min = preferences.get("salary_min")
    job_max = job.get("salary_max")
    if salary_min is None or (job_max is not None and job_max >= salary_min):
        score += 30
        signals["salary_ok"] = True

    return min(score, 100), signals
