from athena_worker.hn_ingest import parse_comment, parse_thread

REAL_COMMENT = {
    "id": 49523712,
    "type": "comment",
    "created_at_i": 1788274914,
    # Exactly as the live Algolia API returns it: literal quotes around
    # attributes, but slashes inside the URL value are &#x2F;-escaped.
    "text": (
        "Modash.io | Senior Product Engineer | Remote (Europe) | Full-time | "
        '£75k–£110k | <a href="https:&#x2F;&#x2F;modash.io" '
        'rel="nofollow">https:&#x2F;&#x2F;modash.io</a><p>Modash helps brands '
        "find, manage, and pay creators."
    ),
}


def test_parse_comment_extracts_pipe_separated_fields():
    job = parse_comment(REAL_COMMENT)
    assert job is not None
    assert job["source"] == "hn"
    assert job["external_id"] == "49523712"
    assert job["company"] == "Modash.io"
    assert job["title"] == "Senior Product Engineer"
    assert job["location"] == "Remote (Europe)"
    assert job["remote"] is True
    assert job["url"] == "https://modash.io"
    assert job["posted_at"] is not None


def test_parse_comment_extracts_salary_range():
    comment = {
        "id": 1,
        "type": "comment",
        "text": "Acme Corp | Backend Engineer | NYC | Onsite | $150k-$190k",
    }
    job = parse_comment(comment)
    assert job["salary_min"] == 150000
    assert job["salary_max"] == 190000


def test_parse_comment_handles_no_pipes_gracefully():
    comment = {"id": 2, "type": "comment", "text": "just a reply, not a job post at all"}
    job = parse_comment(comment)
    assert job is not None
    assert job["company"] == "just a reply, not a job post at all"


def test_parse_comment_returns_none_for_empty_text():
    assert parse_comment({"id": 3, "type": "comment", "text": None}) is None
    assert parse_comment({"id": 4, "type": "comment"}) is None


def test_parse_thread_skips_non_comments_and_dead_deleted():
    thread = {
        "children": [
            {"id": 1, "type": "comment", "text": "A | B | C"},
            {"id": 2, "type": "comment", "text": "D | E | F", "dead": True},
            {"id": 3, "type": "comment", "text": "G | H | I", "deleted": True},
            {"id": 4, "type": "story", "text": "not a comment"},
        ]
    }
    rows = parse_thread(thread)
    assert len(rows) == 1
    assert rows[0]["external_id"] == "1"


# --- Regression: posts that don't follow `Company | Role | Location` order.
# Each of these landed a URL (or a role list) in the wrong column before
# `_split_fields` classified parts by shape instead of by position.


def test_url_in_second_position_is_not_treated_as_the_title():
    comment = {
        "id": 10,
        "type": "comment",
        "text": "Monumint (YC W24) | https://monumint.com | Full Stack Engineers | REMOTE",
    }
    job = parse_comment(comment)
    assert job["company"] == "Monumint (YC W24)"
    assert job["title"] == "Full Stack Engineers"
    assert job["location"] == "REMOTE"
    assert job["remote"] is True


def test_location_before_role_is_not_swapped():
    comment = {
        "id": 11,
        "type": "comment",
        "text": "Mechanize | San Francisco, CA (Onsite) | Junior SWE, Research Engineer",
    }
    job = parse_comment(comment)
    assert job["company"] == "Mechanize"
    assert job["title"] == "Junior SWE, Research Engineer"
    assert job["location"] == "San Francisco, CA (Onsite)"


def test_bare_domain_is_recognised_as_a_url_not_a_title():
    comment = {
        "id": 12,
        "type": "comment",
        "text": "Category Labs | www.category.xyz | Senior Engineer | Remote and NYC",
    }
    job = parse_comment(comment)
    assert job["title"] == "Senior Engineer"
    assert job["location"] == "Remote and NYC"


def test_employment_type_and_salary_parts_are_not_mistaken_for_location():
    comment = {
        "id": 13,
        "type": "comment",
        "text": "Acme | Full-time | $150k-$190k | Backend Engineer | Berlin",
    }
    job = parse_comment(comment)
    assert job["title"] == "Backend Engineer"
    assert job["location"] == "Berlin"
    assert job["salary_min"] == 150000
    assert job["salary_max"] == 190000


def test_role_wins_over_location_when_a_part_contains_both():
    comment = {"id": 14, "type": "comment", "text": "Globex | Remote Frontend Engineer | UK"}
    job = parse_comment(comment)
    assert job["title"] == "Remote Frontend Engineer"
    assert job["location"] == "UK"
