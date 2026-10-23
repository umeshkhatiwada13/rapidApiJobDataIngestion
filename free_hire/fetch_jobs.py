import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://freehire.me/api/v1/jobs/search"

TECH_CATEGORIES = [
    "software_engineering",
    "backend",
    "frontend",
    "fullstack",
    "mobile",
    "data_engineering",
    "data_science",
    "data_analytics",
    "qa",
    "security",
    "network_engineering",
    "sre",
    "devops",
    "ai_engineering",
    "ml_ai",
    "cloud",
]

PAGE_SIZE = 100
OUTPUT_FILE = Path(__file__).resolve().parent / "data" / "jobs.json"

BASE_PARAMS = {
    "regions": "north_america",
    "category": ",".join(TECH_CATEGORIES),
    "sort": "posted_at",
    "order": "desc",
    "limit": PAGE_SIZE,
}


def parse_datetime(value):
    """Parse an ISO datetime string into a timezone-aware datetime."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
    except (ValueError, TypeError):
        return None


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    all_recent_jobs = []
    seen_slugs = set()
    offset = 0

    with requests.Session() as session:
        while True:
            params = {
                **BASE_PARAMS,
                "offset": offset,
            }

            response = session.get(
                BASE_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            page_jobs = result.get("data", [])

            if not page_jobs:
                break

            reached_older_jobs = False

            for job in page_jobs:
                posted_at = parse_datetime(job.get("posted_at"))

                # Skip jobs whose posting date is unavailable.
                if posted_at is None:
                    continue

                # Results are sorted newest first.
                if posted_at < cutoff:
                    reached_older_jobs = True
                    continue

                slug = job.get("public_slug")

                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    all_recent_jobs.append(job)

            print(
                f"Checked {len(page_jobs)} jobs "
                f"(offset {offset}); "
                f"recent jobs collected: {len(all_recent_jobs)}"
            )

            # Stop once this page contains jobs older than 24 hours.
            if reached_older_jobs:
                break

            # Advance by the number of records returned.
            offset += len(page_jobs)

            # Avoid making requests too quickly.
            time.sleep(0.2)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(all_recent_jobs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n--- Fetch Summary ---")
    print(f"Window start (UTC): {cutoff.isoformat()}")
    print(f"Window end (UTC):   {now.isoformat()}")
    print(f"Recent jobs fetched: {len(all_recent_jobs)}")
    print(f"Saved to: {OUTPUT_FILE.resolve()}")

    if not all_recent_jobs:
        print("No jobs posted in the last 24 hours were found.")


if __name__ == "__main__":
    main()