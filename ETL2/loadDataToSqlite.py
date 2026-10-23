import json
import os
import sqlite3


def store_job_to_sqlite():
  db_file = "jobs_2.db"

  # 1. Read saved JSON file
  if not os.path.exists("jsearch_response_2.json"):
    print("Error: jsearch_response_2.json not found.")
    return

  with open("jsearch_response_2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

  # Fix: Handle both list root structures and dictionary root structures safely
  if isinstance(data, list):
    jobs = data
  elif isinstance(data, dict):
    jobs = data.get("data", {}).get("jobs", [])
  else:
    jobs = []

  print(f"Found {len(jobs)} jobs in JSON file.")

  if not jobs:
    print("No jobs to process. Exiting.")
    return

  # 2. Connect to SQLite
  conn = sqlite3.connect(db_file)
  cursor = conn.cursor()

  # 3. Create table structure tailored for active job records
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_jobs (
            id INTEGER PRIMARY KEY,
            title TEXT,
            organization TEXT,
            location TEXT,
            date_posted TEXT,
            url TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_unit TEXT,
            experience_level TEXT,
            work_arrangement TEXT,
            core_responsibilities TEXT,
            requirements_summary TEXT,
            skills TEXT
        )
    """)

  # 4. Insert records (Note: Moved conn.commit() and conn.close() OUTSIDE the loop for performance!)
  count = 0
  for job in jobs:
    # Extract nested location string safely
    location_str = "Unknown Location"
    if job.get("locations"):
      addr = job["locations"][0].get("address", {})
      location_str = (
          f"{addr.get('addressLocality')}, {addr.get('addressRegion')},"
          f" {addr.get('addressCountry')}"
      )

    # Convert list of skills into a comma-separated string
    skills_str = ", ".join(job.get("ai_key_skills", []))

    cursor.execute(
        """
            INSERT OR REPLACE INTO active_jobs (
                id, title, organization, location, date_posted, url, 
                salary_min, salary_max, salary_unit, experience_level, 
                work_arrangement, core_responsibilities, requirements_summary, skills
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("id"),
            job.get("title"),
            job.get("organization"),
            location_str,
            job.get("date_posted"),
            job.get("url"),
            job.get("ai_salary_min_value"),
            job.get("ai_salary_max_value"),
            job.get("ai_salary_unit_text"),
            job.get("ai_experience_level"),
            job.get("ai_work_arrangement"),
            job.get("ai_core_responsibilities"),
            job.get("ai_requirements_summary"),
            skills_str,
        ),
    )
    count += 1
    print(
        f"Processed job ID {job.get('id')} ({job.get('title')} at"
        f" {job.get('organization')})"
    )

  # Commit and close connection outside the loop once done
  conn.commit()
  conn.close()
  print(f"\nSuccessfully stored all {count} jobs into SQLite database!")


if __name__ == "__main__":
  store_job_to_sqlite()