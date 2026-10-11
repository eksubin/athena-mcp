"""Turns an uploaded resume file into rows for `profile_facts`.

Heuristic, not a full resume parser — same "best-effort, not a guarantee"
posture as the HN worker's parsing (see worker/athena_worker/hn_ingest.py).
No OCR: a scanned/image-only PDF yields little or no text.
"""

import re
from pathlib import Path

import pypdf
from docx import Document

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?", re.IGNORECASE)
_SKILLS_HEADERS = {"skills", "technical skills", "core competencies"}


def extract_text(path: Path, suffix: str) -> str:
    if suffix == ".pdf":
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"unsupported suffix {suffix!r}")


def parse_facts(text: str) -> list[dict]:
    """Contact info and a skills line — not a full resume parse. Confidence
    reflects how much each guess can be trusted: a regex match on
    structured-looking text (an email, a linkedin.com URL) is reliable;
    "the first line is probably the candidate's name" is a much weaker bet.
    """
    facts: list[dict] = []

    email = _EMAIL_RE.search(text)
    if email:
        facts.append({"key": "email", "value": email.group(0), "confidence": 0.95})

    phone = _PHONE_RE.search(text)
    if phone:
        facts.append({"key": "phone", "value": phone.group(0).strip(), "confidence": 0.7})

    linkedin = _LINKEDIN_RE.search(text)
    if linkedin:
        facts.append({"key": "linkedin_url", "value": linkedin.group(0), "confidence": 0.9})

    github = _GITHUB_RE.search(text)
    if github:
        facts.append({"key": "github_url", "value": github.group(0), "confidence": 0.9})

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        first_line = lines[0]
        looks_like_a_name = (
            len(first_line) <= 60
            and "@" not in first_line
            and first_line.lower().rstrip(":") not in _SKILLS_HEADERS
        )
        if looks_like_a_name:
            facts.append({"key": "name", "value": first_line, "confidence": 0.4})

    skills = _extract_section(lines, _SKILLS_HEADERS)
    if skills:
        facts.append({"key": "skills", "value": skills, "confidence": 0.5})

    return facts


def _extract_section(lines: list[str], headers: set[str]) -> str | None:
    """Lines immediately after a matching section header, stopping at
    whatever looks like the next header (short, all-caps)."""
    for i, line in enumerate(lines):
        if line.lower().rstrip(":") not in headers:
            continue
        collected = []
        for candidate in lines[i + 1 : i + 6]:
            if candidate.isupper() and len(candidate.split()) <= 4:
                break
            collected.append(candidate)
        if collected:
            return " ".join(collected)[:500]
    return None
