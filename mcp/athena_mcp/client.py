import httpx

from athena_mcp.config import Settings


class AthenaClient:
    """Every method here is a single HTTP call to the Athena backend — the
    backend does the ranking, filtering, and summarizing. Nothing in this
    class ever loops over raw scraped listings."""

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

    def save_job(self, job_id: str) -> dict:
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
        application = self._find_application(job_id) or self.save_job(job_id)
        job = self.get_job(job_id)
        answers = self._http.get("/answers")
        answers.raise_for_status()
        return {"job": job, "application": application, "answers": answers.json()}

    def record_answer(self, question: str, answer: str, sensitive: bool = False) -> dict:
        r = self._http.post(
            "/answers", json={"question": question, "answer": answer, "sensitive": sensitive}
        )
        r.raise_for_status()
        return r.json()

    def update_status(self, job_id: str, status: str, note: str | None = None) -> dict:
        application = self._find_application(job_id) or self.save_job(job_id)
        r = self._http.patch(
            f"/applications/{application['id']}", json={"status": status, "note": note}
        )
        r.raise_for_status()
        return r.json()

    def get_profile(self) -> dict:
        r = self._http.get("/profile")
        r.raise_for_status()
        return r.json()
