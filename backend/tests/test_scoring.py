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


# --- Behaviour added when the placeholder scorer was replaced.


def test_unknown_salary_gets_partial_credit_not_zero():
    """Most listings don't publish a range; a hard zero buried all of them."""
    known = {"title": "Backend Engineer", "remote": False, "salary_max": 200000}
    unknown = {"title": "Backend Engineer", "remote": False, "salary_max": None}
    prefs = {"salary_min": 150000}

    known_score, known_sig = score_job(known, prefs)
    unknown_score, unknown_sig = score_job(unknown, prefs)

    assert 0 < unknown_score < known_score
    assert unknown_sig["salary"] == "unknown"
    assert "salary_ok" not in unknown_sig
    assert known_sig["salary_ok"] is True


def test_title_matching_is_order_free():
    prefs = {"titles": ["imaging scientist"]}
    reordered, signals = score_job({"title": "Senior Scientist, Imaging", "remote": False}, prefs)
    assert signals["title_match"] is True
    assert signals["title_overlap"] == 1.0
    assert reordered > score_job({"title": "Warehouse Associate", "remote": False}, prefs)[0]


def test_partial_title_overlap_scores_between_miss_and_match():
    prefs = {"titles": ["machine learning engineer"]}
    full = score_job({"title": "Machine Learning Engineer", "remote": False}, prefs)[0]
    partial = score_job({"title": "Machine Learning Intern", "remote": False}, prefs)[0]
    miss = score_job({"title": "Account Executive", "remote": False}, prefs)[0]
    assert miss < partial < full


def test_older_postings_decay_but_are_not_eliminated():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    job = {"title": "Backend Engineer", "remote": False, "salary_max": 200000}
    prefs = {"titles": ["backend engineer"], "salary_min": 150000}

    fresh = score_job({**job, "posted_at": (now - timedelta(days=2)).isoformat()}, prefs)
    stale = score_job({**job, "posted_at": (now - timedelta(days=200)).isoformat()}, prefs)

    assert fresh[0] > stale[0] > 0
    assert fresh[1]["recency_factor"] == 1.0
    assert stale[1]["recency_factor"] == 0.6


def test_missing_posted_at_is_not_penalised():
    job = {"title": "Backend Engineer", "remote": True, "salary_max": 180000}
    prefs = {"titles": ["backend engineer"], "remote_only": True, "salary_min": 150000}
    score, signals = score_job(job, prefs)
    assert score == 100
    assert signals["recency_factor"] == 1.0


def test_source_weight_demotes_a_distrusted_feed():
    job = {"title": "Backend Engineer", "remote": False, "salary_max": 200000, "source": "hn"}
    prefs = {"titles": ["backend engineer"], "salary_min": 150000}
    plain = score_job(job, prefs)[0]
    demoted = score_job(job, {**prefs, "source_weights": {"hn": 0.5}})[0]
    assert demoted < plain


def test_source_weight_is_clamped_against_junk_values():
    job = {"title": "Backend Engineer", "remote": False, "source": "hn"}
    for junk in ({"hn": 99}, {"hn": -5}, {"hn": "nonsense"}, None):
        _, signals = score_job(job, {"source_weights": junk})
        assert 0.5 <= signals["source_weight"] <= 1.5


def test_remote_only_still_zeroes_a_non_remote_job():
    prefs = {"titles": ["backend engineer"], "remote_only": True}
    _, signals = score_job({"title": "Backend Engineer", "remote": False}, prefs)
    assert signals["remote_points"] == 0
    assert "remote_match" not in signals
