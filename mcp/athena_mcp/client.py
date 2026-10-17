import re
from urllib.parse import urlsplit

import httpx

from athena_mcp.config import Settings


class AthenaClient:
    """Typed API calls and small workflow bundles. Ranking and extracted
    profile facts stay on the backend; browser actions stay in BrowserOS."""

    def __init__(self, settings: Settings):
        self._http = httpx.Client(
            base_url=settings.api_url,
            headers={"Authorization": f"Bearer {settings.token}"},
            timeout=20.0,
        )

    def search_jobs(self, limit: int = 10) -> list[dict]:
        r = self._http.get("/jobs", params={"limit": limit})
        r.raise_for_status()
        return r.json()

    def get_job(self, job_id: str) -> dict:
        r = self._http.get(f"/jobs/{job_id}")
        r.raise_for_status()
        return r.json()

    def import_linkedin_job(self, url: str, title: str, company: str, location: str | None = None) -> dict:
        parsed = urlsplit(url)
        match = re.fullmatch(r"/jobs/view/(\d+)/?", parsed.path)
        if parsed.scheme != "https" or parsed.hostname not in {"linkedin.com", "www.linkedin.com"} or not match:
            raise ValueError("Use a LinkedIn job URL: https://www.linkedin.com/jobs/view/123456789/")
        if not title.strip() or not company.strip():
            raise ValueError("Title and company must come from the observed listing")
        job_id = match.group(1)
        r = self._http.post("/jobs", json=[{
            "source": "linkedin", "external_id": job_id,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "title": title.strip(), "company": company.strip(), "location": location,
        }])
        r.raise_for_status()
        return r.json()[0]

    def save_job(self, job_id: str) -> dict:
        existing = self._find_application(job_id)
        if existing:
            return existing
        r = self._http.post("/applications", json={"job_id": job_id})
        r.raise_for_status()
        return r.json()

    def get_queue(self, status: str | None = None) -> list[dict]:
        params = {"status": status} if status else {}
        r = self._http.get("/applications", params=params)
        r.raise_for_status()
        return r.json()

    def _find_application(self, job_id: str) -> dict | None:
        return next((a for a in self.get_queue() if a["job_id"] == job_id), None)

    def start_application(self, job_id: str) -> dict:
        application = self.save_job(job_id)
        job = self.get_job(job_id)
        answers = self._http.get("/answers")
        answers.raise_for_status()
        return {"job": job, "application": application, "answers": answers.json(),
                "profile": self.get_profile(), "submitted": False,
                "next_step": "Prepare the employer form in BrowserOS. This tool does not submit an application."}

    def record_answer(self, question: str, answer: str, sensitive: bool = False) -> dict:
        r = self._http.post(
            "/answers", json={"question": question, "answer": answer, "sensitive": sensitive}
        )
        r.raise_for_status()
        return r.json()

    def update_status(self, job_id: str, status: str, note: str | None = None) -> dict:
        application = self.save_job(job_id)
        r = self._http.patch(
            f"/applications/{application['id']}", json={"status": status, "note": note}
        )
        r.raise_for_status()
        return r.json()

    def get_profile(self) -> dict:
        r = self._http.get("/profile")
        r.raise_for_status()
        facts = self._http.get("/profile/facts")
        facts.raise_for_status()
        return {**r.json(), "facts": facts.json()}
