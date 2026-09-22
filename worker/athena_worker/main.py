import logging
import time

import httpx
from supabase import create_client

from athena_worker.config import Settings
from athena_worker.hn_ingest import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("athena_worker")


def main() -> None:
    settings = Settings()
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    while True:
        try:
            with httpx.Client(timeout=20.0, headers={"User-Agent": "athena-worker/0.1"}) as client:
                count = run(client, supabase)
            log.info("ingested %d HN listings", count)
        except Exception:
            log.exception("HN ingestion run failed")
        time.sleep(settings.interval_seconds)


if __name__ == "__main__":
    main()
