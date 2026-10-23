import sqlite3
from collections import Counter


def extract_all_skills_dynamically(db_file="jobs_2.db"):
    """Dynamically reads and counts every unique skill provided in the database."""
    print("Dynamically discovering and aggregating all skills from job records...")

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Get total job count
        cursor.execute("SELECT COUNT(*) FROM active_jobs")
        role_count = cursor.fetchone()[0]

        if role_count == 0:
            print("No job records found in the database.")
            conn.close()
            return

        # Fetch the pre-extracted skills column from all rows
        cursor.execute("SELECT skills FROM active_jobs WHERE skills IS NOT NULL AND skills != ''")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return

    skill_counter = Counter()
    jobs_with_skills_count = len(rows)

    # Parse and count every single skill dynamically
    for (skills_str,) in rows:
        # Split comma-separated skills string back into a list and clean whitespace
        individual_skills = [s.strip() for s in skills_str.split(",")]

        # Use a set for this specific job to prevent counting duplicate mentions in the same posting
        for skill in set(individual_skills):
            if skill:
                skill_counter[skill] += 1

    # Dynamic Report Header
    print(f"\n=================================================================")
    print(f"  FULLY DYNAMIC DISCOVERED SKILLS REPORT")
    print(f"  Total Postings in DB: {role_count} | Postings with Skill Data: {jobs_with_skills_count}")
    print(f"=================================================================")

    # Display top 25 skills dynamically found in your dataset
    for skill, count in skill_counter.most_common(25):
        percentage = (count / role_count) * 100
        bar_length = int(percentage // 3)  # Scaled for visibility
        bar = "█" * bar_length

        print(f"{skill:<35} | {count:3d} jobs ({percentage:5.1f}%) -> {bar}")

    print("=" * 65)


if __name__ == "__main__":
    extract_all_skills_dynamically()