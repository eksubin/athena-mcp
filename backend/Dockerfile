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
# Named Docker volumes are root-owned by default. Docker initializes a
# *fresh* volume's contents (including ownership) from whatever already
# exists at the mount point in the image, so creating it here with the
# right owner — before docker-compose mounts /data/resumes over it — is
# what makes the app (running as athena, not root) able to write into it.
RUN mkdir -p /data/resumes && chown athena:athena /data/resumes
USER athena
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
