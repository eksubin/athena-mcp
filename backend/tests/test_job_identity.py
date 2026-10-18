import pytest

from app.services.jobs import UnusableJobUrl, identify_listing


def test_linkedin_listing_url_uses_its_job_id():
    assert identify_listing("https://www.linkedin.com/jobs/view/4123456789/") == (
        "linkedin",
        "4123456789",
    )


def test_linkedin_tracking_params_do_not_change_identity():
    """The same listing saved twice from a results page must stay one row."""
    first = identify_listing(
        "https://www.linkedin.com/jobs/view/4123456789/?refId=abc&trackingId=xyz"
    )
    second = identify_listing("https://linkedin.com/jobs/view/4123456789")
    assert first == second == ("linkedin", "4123456789")


def test_linkedin_search_page_resolves_to_the_selected_job():
    assert identify_listing(
        "https://www.linkedin.com/jobs/search/?currentJobId=4123456789&keywords=python"
    ) == ("linkedin", "4123456789")


def test_greenhouse_and_lever_get_their_own_identifiers():
    assert identify_listing("https://boards.greenhouse.io/acme/jobs/7654321") == (
        "greenhouse",
        "acme/7654321",
    )
    assert identify_listing(
        "https://jobs.lever.co/acme/0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"
    ) == ("lever", "acme/0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0")


def test_unknown_site_falls_back_to_host_plus_digest():
    source, external_id = identify_listing("https://careers.example.com/openings/42?lang=en")
    assert source == "careers.example.com"
    assert len(external_id) == 32


def test_fallback_ignores_tracking_params_and_trailing_slash():
    a = identify_listing("https://careers.example.com/openings/42/?utm_source=news&ref=mail")
    b = identify_listing("https://www.careers.example.com/openings/42")
    assert a == b


def test_fallback_keeps_meaningful_query_params_apart():
    a = identify_listing("https://careers.example.com/apply?job=42")
    b = identify_listing("https://careers.example.com/apply?job=43")
    assert a != b


def test_non_web_url_is_refused():
    with pytest.raises(UnusableJobUrl):
        identify_listing("linkedin.com/jobs/view/4123456789")
    with pytest.raises(UnusableJobUrl):
        identify_listing("mailto:recruiter@example.com")
