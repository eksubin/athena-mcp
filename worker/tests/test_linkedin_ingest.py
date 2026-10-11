from datetime import datetime, timezone

from athena_worker.linkedin_ingest import (
    parse_relative_date,
    parse_salary,
    split_company_line,
    to_job_row,
    to_job_rows,
)

NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)

# Captured verbatim from the saved-jobs list and the listing page.
REAL_CAPTURE = {
    "external_id": "4466165590",
    "title": "Software Engineer, Healthcare",
    "company_line": "OpenAI · San Francisco, CA (Hybrid)",
    "posted": "1 week ago",
    "apply_label": "Apply",
    "salary_raw": "$347K/yr - $385K/yr",
    "workplace": "Hybrid",
    "description": "About The Team\n\nOpenAI's Healthcare team ...",
}


def test_to_job_row_maps_a_real_capture():
    row = to_job_row(REAL_CAPTURE, now=NOW)
    assert row["source"] == "linkedin"
    assert row["external_id"] == "4466165590"
    assert row["title"] == "Software Engineer, Healthcare"
    assert row["company"] == "OpenAI"
    assert row["location"] == "San Francisco, CA"
    assert row["remote"] is False
    assert row["easy_apply"] is False
    assert row["salary_min"] == 347000
    assert row["salary_max"] == 385000
    assert row["url"] == "https://www.linkedin.com/jobs/view/4466165590/"
    assert row["posted_at"].startswith("2026-09-15")


def test_split_company_line_separates_company_place_and_workplace():
    assert split_company_line("Nscale · New York, NY (Hybrid)") == ("Nscale", "New York, NY", "Hybrid")
    assert split_company_line("Capgemini · Atlanta, GA") == ("Capgemini", "Atlanta, GA", None)
    assert split_company_line("Brillio · United States (Remote)") == (
        "Brillio",
        "United States",
        "Remote",
    )
    assert split_company_line("") == ("", None, None)


def test_remote_flag_comes_from_the_workplace_not_the_location():
    remote = to_job_row({**REAL_CAPTURE, "company_line": "Healthedge · United States (Remote)",
                         "workplace": None}, now=NOW)
    assert remote["remote"] is True
    assert remote["location"] == "United States"


def test_easy_apply_is_read_from_the_button_label():
    assert to_job_row({**REAL_CAPTURE, "apply_label": "Easy Apply"}, now=NOW)["easy_apply"] is True
    assert to_job_row({**REAL_CAPTURE, "apply_label": "Apply"}, now=NOW)["easy_apply"] is False


def test_parse_salary_handles_k_suffix_and_plain_amounts():
    assert parse_salary("$347K/yr - $385K/yr") == (347000, 385000)
    assert parse_salary("$178.5K/yr - $257.8K/yr") == (178500, 257800)
    assert parse_salary("$150,000/yr - $200,000/yr") == (150000, 200000)
    assert parse_salary("$200K/yr") == (200000, 200000)


def test_parse_salary_ignores_hourly_rates():
    """An hourly figure isn't comparable to a yearly floor, so it's dropped."""
    assert parse_salary("$60/hr - $80/hr") == (None, None)


def test_parse_salary_returns_none_when_absent():
    assert parse_salary(None) == (None, None)
    assert parse_salary("") == (None, None)
    assert parse_salary("Competitive") == (None, None)


def test_parse_relative_date_handles_linkedin_wordings():
    assert parse_relative_date("Posted 6d ago", NOW).startswith("2026-09-16")
    assert parse_relative_date("6 days ago", NOW).startswith("2026-09-16")
    assert parse_relative_date("Reposted 1 week ago", NOW).startswith("2026-09-15")
    assert parse_relative_date("3 weeks ago", NOW).startswith("2026-09-01")
    assert parse_relative_date("2mo ago", NOW).startswith("2026-07-24")  # 2 x 30 days


def test_parse_relative_date_returns_none_when_unparseable():
    assert parse_relative_date(None, NOW) is None
    assert parse_relative_date("recently", NOW) is None


def test_to_job_row_rejects_captures_it_cannot_identify():
    assert to_job_row({"title": "X", "company": "Y"}, now=NOW) is None      # no id
    assert to_job_row({"external_id": "1", "company": "Y"}, now=NOW) is None  # no title
    assert to_job_row({"external_id": "1", "title": "X"}, now=NOW) is None    # no company


def test_to_job_rows_deduplicates_repeated_listings():
    """Re-reading a paginated list can hand the same listing back twice, and
    an upsert batch that repeats the conflict key fails outright."""
    rows = to_job_rows([REAL_CAPTURE, dict(REAL_CAPTURE), {"external_id": ""}], now=NOW)
    assert len(rows) == 1
    assert rows[0]["external_id"] == "4466165590"
