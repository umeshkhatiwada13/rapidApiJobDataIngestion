import json
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg
from psycopg.types.json import Jsonb

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "jobs.json"
ENV_FILE = BASE_DIR.parent / ".env"

load_dotenv(ENV_FILE, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(f"DATABASE_URL not found in {ENV_FILE}")

print("Database URL loaded:", True)
print("Database name:", DATABASE_URL.rsplit("/", 1)[-1].split("?")[0])

# --------------------------------------------------
# Create table and indexes if they do not exist
# --------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.jobs (
    id BIGSERIAL PRIMARY KEY,
    public_slug TEXT NOT NULL UNIQUE,
    external_id TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    title TEXT NOT NULL,
    company TEXT,
    company_slug TEXT,
    location TEXT,
    description TEXT,
    countries JSONB NOT NULL DEFAULT '[]'::jsonb,
    regions JSONB NOT NULL DEFAULT '[]'::jsonb,
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    work_mode TEXT,
    is_tech TEXT,
    seniority TEXT,
    category TEXT,
    domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    enrichment JSONB NOT NULL DEFAULT '{}'::jsonb,
    reality JSONB NOT NULL DEFAULT '{}'::jsonb,
    posted_at TIMESTAMPTZ,
    source_created_at TIMESTAMPTZ,
    source_updated_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_posted_at
    ON public.jobs (posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_category
    ON public.jobs (category);

CREATE INDEX IF NOT EXISTS idx_jobs_work_mode
    ON public.jobs (work_mode);

CREATE INDEX IF NOT EXISTS idx_jobs_skills
    ON public.jobs USING GIN (skills);
"""

# --------------------------------------------------
# Insert or update jobs
# --------------------------------------------------

INSERT_SQL = """
INSERT INTO public.jobs (
    public_slug,
    external_id,
    source,
    source_url,
    title,
    company,
    company_slug,
    location,
    description,
    countries,
    regions,
    skills,
    work_mode,
    is_tech,
    seniority,
    category,
    domains,
    requirements,
    enrichment,
    reality,
    posted_at,
    source_created_at,
    source_updated_at,
    last_seen_at,
    closed_at,
    raw_payload
)
VALUES (
    %(public_slug)s,
    %(external_id)s,
    %(source)s,
    %(url)s,
    %(title)s,
    %(company)s,
    %(company_slug)s,
    %(location)s,
    %(description)s,
    %(countries)s,
    %(regions)s,
    %(skills)s,
    %(work_mode)s,
    %(is_tech)s,
    %(seniority)s,
    %(category)s,
    %(domains)s,
    %(requirements)s,
    %(enrichment)s,
    %(reality)s,
    %(posted_at)s,
    %(source_created_at)s,
    %(source_updated_at)s,
    %(last_seen_at)s,
    %(closed_at)s,
    %(raw_payload)s
)
ON CONFLICT (public_slug) DO UPDATE SET
    external_id = EXCLUDED.external_id,
    source = EXCLUDED.source,
    source_url = EXCLUDED.source_url,
    title = EXCLUDED.title,
    company = EXCLUDED.company,
    company_slug = EXCLUDED.company_slug,
    location = EXCLUDED.location,
    description = EXCLUDED.description,
    countries = EXCLUDED.countries,
    regions = EXCLUDED.regions,
    skills = EXCLUDED.skills,
    work_mode = EXCLUDED.work_mode,
    is_tech = EXCLUDED.is_tech,
    seniority = EXCLUDED.seniority,
    category = EXCLUDED.category,
    domains = EXCLUDED.domains,
    requirements = EXCLUDED.requirements,
    enrichment = EXCLUDED.enrichment,
    reality = EXCLUDED.reality,
    posted_at = EXCLUDED.posted_at,
    source_created_at = EXCLUDED.source_created_at,
    source_updated_at = EXCLUDED.source_updated_at,
    last_seen_at = EXCLUDED.last_seen_at,
    closed_at = EXCLUDED.closed_at,
    raw_payload = EXCLUDED.raw_payload,
    updated_at = NOW()
RETURNING (xmax = 0) AS inserted;
"""


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def to_jsonb(value, default):
    return Jsonb(value if value is not None else default)


def prepare_job(job):
    required = ("public_slug", "title", "source")
    missing = [key for key in required if not job.get(key)]

    if missing:
        raise ValueError(
            f"Missing required fields {missing}: "
            f"{job.get('public_slug', 'unknown job')}"
        )

    enrichment = job.get("enrichment") or {}

    return {
        "public_slug": job["public_slug"],
        "external_id": job.get("external_id"),
        "source": job["source"],
        "url": job.get("url"),
        "title": job["title"],
        "company": job.get("company"),
        "company_slug": job.get("company_slug"),
        "location": job.get("location"),
        "description": job.get("description"),
        "countries": to_jsonb(job.get("countries"), []),
        "regions": to_jsonb(job.get("regions"), []),
        "skills": to_jsonb(job.get("skills"), []),
        "work_mode": job.get("work_mode"),
        "is_tech": job.get("is_tech"),
        "seniority": enrichment.get("seniority"),
        "category": enrichment.get("category"),
        "domains": to_jsonb(enrichment.get("domains"), []),
        "requirements": to_jsonb(enrichment.get("requirements"), []),
        "enrichment": Jsonb(enrichment),
        "reality": Jsonb(job.get("reality") or {}),
        "posted_at": job.get("posted_at"),
        "source_created_at": job.get("created_at"),
        "source_updated_at": job.get("updated_at"),
        "last_seen_at": job.get("last_seen_at"),
        "closed_at": job.get("closed_at"),
        "raw_payload": Jsonb(job),
    }


# --------------------------------------------------
# Main ETL process
# --------------------------------------------------

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} not found. Run fetch_jobs.py first."
        )

    jobs = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    if not isinstance(jobs, list):
        raise ValueError("Expected jobs.json to contain a JSON array.")

    inserted = 0
    updated = 0
    failed = 0

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # Create table and indexes before inserting.
            cur.execute(CREATE_TABLE_SQL)
            print("Table and indexes checked/created.")

            for job in jobs:
                cur.execute("SAVEPOINT job_insert")

                try:
                    cur.execute(INSERT_SQL, prepare_job(job))
                    was_inserted = cur.fetchone()[0]

                    cur.execute("RELEASE SAVEPOINT job_insert")

                    if was_inserted:
                        inserted += 1
                    else:
                        updated += 1

                    print(
                        f"{'Inserted' if was_inserted else 'Updated'}: "
                        f"{job.get('title')} - {job.get('company')}"
                    )

                except (ValueError, psycopg.Error, TypeError) as exc:
                    cur.execute("ROLLBACK TO SAVEPOINT job_insert")
                    cur.execute("RELEASE SAVEPOINT job_insert")

                    failed += 1
                    print(
                        f"Failed: {job.get('public_slug', 'unknown')}: "
                        f"{exc}"
                    )

    # The connection context has committed successful database changes.
    print("\n--- Database Insertion Summary ---")
    print(f"Read from file: {len(jobs)}")
    print(f"Inserted:       {inserted}")
    print(f"Updated:        {updated}")
    print(f"Failed:         {failed}")

    # Delete the input file only if every job succeeded.
    if failed == 0:
        INPUT_FILE.unlink()
        print(f"Deleted input file: {INPUT_FILE}")
    else:
        print(
            f"Input file retained because {failed} job(s) failed. "
            "Fix the errors and rerun the ETL."
        )


if __name__ == "__main__":
    main()
