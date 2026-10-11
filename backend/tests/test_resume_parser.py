from pathlib import Path

import pypdf
from docx import Document
from pypdf import PdfWriter

from app.services.resume_parser import extract_text, parse_facts

SAMPLE_RESUME = """Jordan Rivera
jordan.rivera@example.com | (415) 555-0182
linkedin.com/in/jordanrivera | github.com/jordanrivera

SKILLS
Python, PostgreSQL, Docker, FastAPI, React

EXPERIENCE
Senior Backend Engineer, Acme Corp"""


def test_parse_facts_extracts_contact_info():
    facts = {f["key"]: f["value"] for f in parse_facts(SAMPLE_RESUME)}
    assert facts["email"] == "jordan.rivera@example.com"
    assert facts["phone"] == "(415) 555-0182"
    assert facts["linkedin_url"] == "linkedin.com/in/jordanrivera"
    assert facts["github_url"] == "github.com/jordanrivera"
    assert facts["name"] == "Jordan Rivera"


def test_parse_facts_extracts_skills_section():
    facts = {f["key"]: f["value"] for f in parse_facts(SAMPLE_RESUME)}
    assert "Python" in facts["skills"]
    assert "FastAPI" in facts["skills"]


def test_parse_facts_confidence_ordering():
    facts = {f["key"]: f["confidence"] for f in parse_facts(SAMPLE_RESUME)}
    # The name guess is much weaker than a regex match on structured text.
    assert facts["name"] < facts["email"]


def test_parse_facts_handles_empty_text():
    assert parse_facts("") == []


def test_parse_facts_skips_name_when_first_line_is_a_header():
    facts = parse_facts("SKILLS\nPython, Go")
    keys = [f["key"] for f in facts]
    assert "name" not in keys


def test_extract_text_from_real_docx(tmp_path: Path):
    doc = Document()
    doc.add_paragraph("Jordan Rivera")
    doc.add_paragraph("jordan.rivera@example.com")
    doc.add_paragraph("SKILLS")
    doc.add_paragraph("Python, PostgreSQL")
    path = tmp_path / "resume.docx"
    doc.save(str(path))

    text = extract_text(path, ".docx")
    assert "Jordan Rivera" in text
    assert "jordan.rivera@example.com" in text

    facts = {f["key"]: f["value"] for f in parse_facts(text)}
    assert facts["email"] == "jordan.rivera@example.com"


def test_extract_text_from_real_pdf(tmp_path: Path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    path = tmp_path / "resume.pdf"
    with open(path, "wb") as f:
        writer.write(f)

    # A blank page has no text — this just confirms extraction runs against
    # a real PDF without raising, not that it recovers content that isn't
    # there. pypdf has no text-drawing API without an extra dependency, so
    # a genuinely populated PDF isn't exercised here.
    text = extract_text(path, ".pdf")
    assert text == ""
    reader = pypdf.PdfReader(str(path))
    assert len(reader.pages) == 1


def test_extract_text_from_txt(tmp_path: Path):
    path = tmp_path / "resume.txt"
    path.write_text(SAMPLE_RESUME, encoding="utf-8")
    assert extract_text(path, ".txt") == SAMPLE_RESUME


def test_extract_text_rejects_unsupported_suffix(tmp_path: Path):
    path = tmp_path / "resume.rtf"
    path.write_text("x", encoding="utf-8")
    try:
        extract_text(path, ".rtf")
        assert False, "expected ValueError"
    except ValueError:
        pass
