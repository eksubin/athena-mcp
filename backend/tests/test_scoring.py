from app.services.scoring import score_job


def test_score_job_full_match():
    job = {"title": "Senior Backend Engineer", "remote": True, "salary_max": 180000}
    prefs = {"titles": ["backend engineer"], "remote_only": True, "salary_min": 150000}
    score, signals = score_job(job, prefs)
    assert score == 100
    assert signals["title_match"] is True
    assert signals["remote_match"] is True


def test_score_job_no_preferences_still_bounded():
    job = {"title": "Anything", "remote": False, "salary_max": None}
    score, _ = score_job(job, {})
    assert 0 <= score <= 100


def test_score_job_salary_below_floor_not_credited():
    job = {"title": "Backend Engineer", "remote": False, "salary_max": 100000}
    prefs = {"salary_min": 150000}
    score, signals = score_job(job, prefs)
    assert "salary_ok" not in signals
