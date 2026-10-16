import json
import sqlite3
import os


def load_jobs_to_sqlite():
    db_file = "jobs.db"

    # 1. Read saved JSON file
    if not os.path.exists("jsearch_response.json"):
        print("Error: jsearch_response.json not found.")
        return

    with open("jsearch_response.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("data", {}).get("jobs", [])
    print(f"Found {len(jobs)} jobs in JSON file.")

    # 2. Connect to SQLite (creates 'jobs.db' automatically)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 3. Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            posted_date TEXT
        )
    """)

    # 4. Insert records
    count = 0
    for job in jobs:
        cursor.execute("""
            INSERT INTO job_postings (title, company, location, description, posted_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            job.get("job_title", "Software Engineer"),
            job.get("employer_name", "Unknown Company"),
            job.get("job_location", "Toronto, ON"),
            job.get("job_description", ""),
            (job.get("job_posted_at_datetime_utc") or "2026-10-15")[:10]
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"Successfully loaded {count} jobs into local SQLite database ('{db_file}').")


if __name__ == "__main__":
    load_jobs_to_sqlite()