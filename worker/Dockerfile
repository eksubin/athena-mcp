# No Playwright/browser here — HN ingestion only hits the public Algolia
# API (see README), so this stays a plain, small Python image.
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
RUN useradd -m athena
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --chown=athena:athena . /app
USER athena
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
CMD ["python", "-m", "athena_worker.main"]
