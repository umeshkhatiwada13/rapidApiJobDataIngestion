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


# --------------------------------------------------
# Database schema
# --------------------------------------------------

CREATE_COMPANIES_SQL = """
CREATE TABLE IF NOT EXISTS public.companies (
    company_id BIGSERIAL PRIMARY KEY,
    company_key TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    company_slug TEXT
);
"""

CREATE_SKILLS_SQL = """
CREATE TABLE IF NOT EXISTS public.skills (
    skill_id BIGSERIAL PRIMARY KEY,
    skill_key TEXT NOT NULL UNIQUE,
    skill_name TEXT NOT NULL
);
"""

CREATE_COUNTRIES_SQL = """
CREATE TABLE IF NOT EXISTS public.countries (
    country_id BIGSERIAL PRIMARY KEY,
    country_code TEXT UNIQUE,
    country_name TEXT NOT NULL UNIQUE
);
"""

CREATE_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS public.jobs (
    id BIGSERIAL PRIMARY KEY,
    public_slug TEXT NOT NULL UNIQUE,
    external_id TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    title TEXT NOT NULL,
    company_id BIGINT REFERENCES public.companies(company_id),
    location TEXT,
    description TEXT,
    regions JSONB NOT NULL DEFAULT '[]'::jsonb,
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
"""

CREATE_JOB_SKILLS_SQL = """
CREATE TABLE IF NOT EXISTS public.job_skills (
    job_id BIGINT NOT NULL
        REFERENCES public.jobs(id) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL
        REFERENCES public.skills(skill_id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);
"""

CREATE_JOB_COUNTRIES_SQL = """
CREATE TABLE IF NOT EXISTS public.job_countries (
    job_id BIGINT NOT NULL
        REFERENCES public.jobs(id) ON DELETE CASCADE,
    country_id BIGINT NOT NULL
        REFERENCES public.countries(country_id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, country_id)
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at
    ON public.jobs (posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_category
    ON public.jobs (category);

CREATE INDEX IF NOT EXISTS idx_jobs_work_mode
    ON public.jobs (work_mode);

CREATE INDEX IF NOT EXISTS idx_jobs_company_id
    ON public.jobs (company_id);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id
    ON public.job_skills (skill_id);

CREATE INDEX IF NOT EXISTS idx_job_countries_country_id
    ON public.job_countries (country_id);
"""


# --------------------------------------------------
# Migrate existing jobs table
# --------------------------------------------------

MIGRATE_JOBS_SQL = """
ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS company_id BIGINT
        REFERENCES public.companies(company_id);

-- Remove the old duplicated data columns.
-- The original API response remains available in raw_payload.
ALTER TABLE public.jobs
    DROP COLUMN IF EXISTS company;

ALTER TABLE public.jobs
    DROP COLUMN IF EXISTS company_slug;

ALTER TABLE public.jobs
    DROP COLUMN IF EXISTS skills;

ALTER TABLE public.jobs
    DROP COLUMN IF EXISTS countries;

DROP INDEX IF EXISTS public.idx_jobs_skills;
"""


# --------------------------------------------------
# Insert or update jobs
# --------------------------------------------------

INSERT_JOB_SQL = """
INSERT INTO public.jobs (
    public_slug,
    external_id,
    source,
    source_url,
    title,
    company_id,
    location,
    description,
    regions,
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
    %(source_url)s,
    %(title)s,
    %(company_id)s,
    %(location)s,
    %(description)s,
    %(regions)s,
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
    company_id = EXCLUDED.company_id,
    location = EXCLUDED.location,
    description = EXCLUDED.description,
    regions = EXCLUDED.regions,
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
RETURNING id, (xmax = 0) AS inserted;
"""


# --------------------------------------------------
# General helpers
# --------------------------------------------------

def to_jsonb(value, default):
    return Jsonb(value if value is not None else default)


def normalize_text(value):
    """Convert a string to trimmed text; otherwise return None."""
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def normalize_list(value):
    """Accept a list, a single string, or a missing value."""
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    return []


# --------------------------------------------------
# Company normalization
# --------------------------------------------------

def upsert_company(cur, job):
    company = job.get("company")
    company_slug = normalize_text(job.get("company_slug"))

    # Some APIs return a company object instead of a string.
    if isinstance(company, dict):
        company_slug = (
            company_slug
            or normalize_text(company.get("slug"))
        )
        company_name = (
            normalize_text(company.get("name"))
            or normalize_text(company.get("company_name"))
        )
    else:
        company_name = normalize_text(company)

    if not company_name and not company_slug:
        return None

    company_name = company_name or company_slug

    company_key = (
        company_slug.casefold()
        if company_slug
        else company_name.casefold()
    )

    cur.execute(
        """
        INSERT INTO public.companies (
            company_key, company_name, company_slug
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (company_key) DO NOTHING;
        """,
        (company_key, company_name, company_slug),
    )

    cur.execute(
        """
        SELECT company_id
        FROM public.companies
        WHERE company_key = %s;
        """,
        (company_key,),
    )

    row = cur.fetchone()

    if row is None:
        raise RuntimeError(
            f"Could not resolve company: {company_name}"
        )

    return row[0]


# --------------------------------------------------
# Skill normalization
# --------------------------------------------------

def extract_skill(item):
    """Support skill strings and common object formats."""
    if isinstance(item, str):
        return normalize_text(item)

    if isinstance(item, dict):
        return (
            normalize_text(item.get("name"))
            or normalize_text(item.get("skill_name"))
            or normalize_text(item.get("skill"))
        )

    return None


def upsert_skill(cur, skill_name):
    skill_key = skill_name.casefold()

    cur.execute(
        """
        INSERT INTO public.skills (skill_key, skill_name)
        VALUES (%s, %s)
        ON CONFLICT (skill_key) DO NOTHING;
        """,
        (skill_key, skill_name),
    )

    cur.execute(
        """
        SELECT skill_id
        FROM public.skills
        WHERE skill_key = %s;
        """,
        (skill_key,),
    )

    row = cur.fetchone()

    if row is None:
        raise RuntimeError(f"Could not resolve skill: {skill_name}")

    return row[0]


def sync_job_skills(cur, job_id, raw_skills):
    """
    Synchronize the job's skill relationships with the current
    complete skill list from the API.
    """
    skills = normalize_list(raw_skills)

    # Delete previous links so removed skills do not remain attached.
    cur.execute(
        "DELETE FROM public.job_skills WHERE job_id = %s;",
        (job_id,),
    )

    seen = set()

    for item in skills:
        skill_name = extract_skill(item)

        if not skill_name:
            continue

        skill_key = skill_name.casefold()

        if skill_key in seen:
            continue

        seen.add(skill_key)

        skill_id = upsert_skill(cur, skill_name)

        cur.execute(
            """
            INSERT INTO public.job_skills (job_id, skill_id)
            VALUES (%s, %s)
            ON CONFLICT (job_id, skill_id) DO NOTHING;
            """,
            (job_id, skill_id),
        )


# --------------------------------------------------
# Country normalization
# --------------------------------------------------

def extract_country(item):
    """Return (country_name, country_code)."""
    if isinstance(item, str):
        return normalize_text(item), None

    if isinstance(item, dict):
        name = (
            normalize_text(item.get("country_name"))
            or normalize_text(item.get("name"))
            or normalize_text(item.get("country"))
        )

        code = (
            normalize_text(item.get("country_code"))
            or normalize_text(item.get("code"))
            or normalize_text(item.get("iso2"))
        )

        if code:
            code = code.upper()

        return name, code

    return None, None


def upsert_country(cur, country_name, country_code=None):
    """
    Resolve countries by ISO code when available, otherwise by name.
    Existing records are reused rather than duplicated.
    """
    if country_code:
        cur.execute(
            """
            SELECT country_id
            FROM public.countries
            WHERE country_code = %s
               OR LOWER(country_name) = LOWER(%s)
            ORDER BY
                CASE WHEN country_code = %s THEN 0 ELSE 1 END
            LIMIT 1;
            """,
            (country_code, country_name, country_code),
        )
    else:
        cur.execute(
            """
            SELECT country_id
            FROM public.countries
            WHERE LOWER(country_name) = LOWER(%s)
            LIMIT 1;
            """,
            (country_name,),
        )

    row = cur.fetchone()

    if row:
        return row[0]

    # Insert new country. ON CONFLICT handles concurrent or
    # case-sensitive uniqueness conflicts safely.
    cur.execute(
        """
        INSERT INTO public.countries (country_code, country_name)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        RETURNING country_id;
        """,
        (country_code, country_name),
    )

    row = cur.fetchone()

    if row:
        return row[0]

    # A unique constraint may have won a concurrent insert.
    if country_code:
        cur.execute(
            """
            SELECT country_id
            FROM public.countries
            WHERE country_code = %s
               OR LOWER(country_name) = LOWER(%s)
            ORDER BY
                CASE WHEN country_code = %s THEN 0 ELSE 1 END
            LIMIT 1;
            """,
            (country_code, country_name, country_code),
        )
    else:
        cur.execute(
            """
            SELECT country_id
            FROM public.countries
            WHERE LOWER(country_name) = LOWER(%s)
            LIMIT 1;
            """,
            (country_name,),
        )

    row = cur.fetchone()

    if row is None:
        raise RuntimeError(f"Could not resolve country: {country_name}")

    return row[0]


def sync_job_countries(cur, job_id, raw_countries):
    """
    Synchronize a job's country relationships with its current
    complete country list.
    """
    countries = normalize_list(raw_countries)

    cur.execute(
        "DELETE FROM public.job_countries WHERE job_id = %s;",
        (job_id,),
    )

    seen = set()

    for item in countries:
        country_name, country_code = extract_country(item)

        if not country_name:
            continue

        country_key = (
            country_code.casefold()
            if country_code
            else country_name.casefold()
        )

        if country_key in seen:
            continue

        seen.add(country_key)

        country_id = upsert_country(
            cur,
            country_name,
            country_code,
        )

        cur.execute(
            """
            INSERT INTO public.job_countries (job_id, country_id)
            VALUES (%s, %s)
            ON CONFLICT (job_id, country_id) DO NOTHING;
            """,
            (job_id, country_id),
        )


# --------------------------------------------------
# Prepare job for insertion
# --------------------------------------------------

def prepare_job(job, company_id):
    required = ("public_slug", "title", "source")
    missing = [
        key for key in required
        if not normalize_text(job.get(key))
    ]

    if missing:
        raise ValueError(
            f"Missing required fields {missing}: "
            f"{job.get('public_slug', 'unknown job')}"
        )

    enrichment = job.get("enrichment") or {}

    if not isinstance(enrichment, dict):
        enrichment = {}

    return {
        "public_slug": job["public_slug"].strip(),
        "external_id": job.get("external_id"),
        "source": job["source"].strip(),
        "source_url": job.get("url"),
        "title": job["title"].strip(),
        "company_id": company_id,
        "location": job.get("location"),
        "description": job.get("description"),
        "regions": to_jsonb(job.get("regions"), []),
        "work_mode": job.get("work_mode"),
        "is_tech": job.get("is_tech"),
        "seniority": enrichment.get("seniority"),
        "category": enrichment.get("category"),
        "domains": to_jsonb(enrichment.get("domains"), []),
        "requirements": to_jsonb(
            enrichment.get("requirements"), []
        ),
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
    skill_links = 0
    country_links = 0

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # Create parent tables before dependent tables.
            cur.execute(CREATE_COMPANIES_SQL)
            cur.execute(CREATE_SKILLS_SQL)
            cur.execute(CREATE_COUNTRIES_SQL)
            cur.execute(CREATE_JOBS_SQL)

            # Adapt an existing jobs table to the normalized schema.
            cur.execute(MIGRATE_JOBS_SQL)

            cur.execute(CREATE_JOB_SKILLS_SQL)
            cur.execute(CREATE_JOB_COUNTRIES_SQL)
            cur.execute(CREATE_INDEXES_SQL)

            print("Database schema checked/created.")

            for job in jobs:
                cur.execute("SAVEPOINT job_insert")

                try:
                    if not isinstance(job, dict):
                        raise ValueError("Job record is not a JSON object.")

                    # Phase 1: resolve company.
                    company_id = upsert_company(cur, job)

                    # Phase 2: insert or update job.
                    cur.execute(
                        INSERT_JOB_SQL,
                        prepare_job(job, company_id),
                    )

                    job_id, was_inserted = cur.fetchone()

                    # Phase 3: normalize skill relationships.
                    if "skills" in job:
                        sync_job_skills(
                            cur,
                            job_id,
                            job.get("skills"),
                        )

                    # Phase 4: normalize country relationships.
                    if "countries" in job:
                        sync_job_countries(
                            cur,
                            job_id,
                            job.get("countries"),
                        )

                    cur.execute("RELEASE SAVEPOINT job_insert")

                    if was_inserted:
                        inserted += 1
                    else:
                        updated += 1

                    print(
                        f"{'Inserted' if was_inserted else 'Updated'}: "
                        f"{job.get('title')} - "
                        f"{job.get('company')}"
                    )

                except (ValueError, TypeError, KeyError,
                        psycopg.Error, RuntimeError) as exc:

                    cur.execute(
                        "ROLLBACK TO SAVEPOINT job_insert"
                    )
                    cur.execute(
                        "RELEASE SAVEPOINT job_insert"
                    )

                    failed += 1

                    print(
                        f"Failed: "
                        f"{job.get('public_slug', 'unknown')}: {exc}"
                    )

            # Counts are measured after all successful job operations.
            cur.execute("SELECT COUNT(*) FROM public.job_skills;")
            skill_links = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM public.job_countries;")
            country_links = cur.fetchone()[0]

    # The connection context commits successful changes before here.
    print("\n--- ETL Summary ---")
    print(f"Jobs read:             {len(jobs)}")
    print(f"Jobs inserted:         {inserted}")
    print(f"Jobs updated:          {updated}")
    print(f"Jobs failed:           {failed}")
    print(f"Total job-skill links: {skill_links}")
    print(f"Total job-country links: {country_links}")

    # Delete the source only if all jobs succeeded.
    if failed == 0:
        INPUT_FILE.unlink()
        print(f"Deleted input file: {INPUT_FILE}")
    else:
        print(
            f"Input file retained: {failed} job(s) failed. "
            "Fix the errors and rerun the ETL."
        )


if __name__ == "__main__":
    main()