from mcp.server.mcpserver import MCPServer

from athena_mcp.client import AthenaClient
from athena_mcp.config import Settings

settings = Settings()
client = AthenaClient(settings)
mcp = MCPServer("athena")


@mcp.tool()
def search_jobs(limit: int = 10) -> list[dict]:
    """Ranked, pre-scored jobs from Athena: id, title, company, score,
    location, salary, easy_apply. Full descriptions are NOT included — call
    get_job for one specific listing only when you actually need it."""
    return client.search_jobs(limit=limit)


@mcp.tool()
def get_job(job_id: str) -> dict:
    """Full detail for one job: description, URL, posted date."""
    return client.get_job(job_id)


@mcp.tool()
def save_job(job_id: str) -> dict:
    """Mark a job as saved, without applying yet."""
    return client.save_job(job_id)


@mcp.tool()
def get_queue(status: str | None = None) -> list[dict]:
    """Applications, optionally filtered by status: saved, applied, pending,
    interview, offer, or rejected."""
    return client.get_queue(status=status)


@mcp.tool()
def start_application(job_id: str) -> dict:
    """Everything needed to fill out this application: the job, the
    (possibly newly-created) application record, and the full Q&A answer
    bank — so the browser-driven form-fill step doesn't have to ask the
    user questions Athena already knows the answer to."""
    return client.start_application(job_id)


@mcp.tool()
def record_answer(question: str, answer: str, sensitive: bool = False) -> dict:
    """Save a reusable answer to the Q&A bank. Mark salary/visa/etc as
    sensitive=True — the plugin still confirms those with the user each
    time rather than reusing them silently."""
    return client.record_answer(question, answer, sensitive)


@mcp.tool()
def update_status(job_id: str, status: str, note: str | None = None) -> dict:
    """Move an application to a new status: saved, applied, pending,
    interview, offer, or rejected. Also grows the user's plot in the
    shared world."""
    return client.update_status(job_id, status, note)


@mcp.tool()
def get_profile() -> dict:
    """Condensed structured profile facts — not the raw CV text."""
    return client.get_profile()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
