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
